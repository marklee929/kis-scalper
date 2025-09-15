import websocket
import threading
import json
import time
from core.position_manager import RealPositionManager
from utils.logger import logger
from api.kis_api import KISApi
from web_socket.market_cache import MarketCache
from data.data_logger import data_logger
from data.event_logger import event_logger
from typing import Optional, Set, Iterable, Dict, Any
import inspect

class KISWebSocketClient:
    """
    KIS 실시간 WebSocket 클라이언트.
    - 자동 재연결 (지수 백오프, 접속 키 갱신 포함)
    - 구독 유지/중복 방지
    - heartbeat (ping)
    """
    def __init__(
        self,
        config, # config 객체 추가
        account_manager,  # <-- KISApi 대신 AccountManager로 변경
        approval_key: str,  # main에서 반드시 전달
        codes: Iterable[str] = None, # 초기 구독 종목
        tr_id: str = "H0STCNT0", # 기본 TR_ID (실시간 체결가)
        custtype: str = "P",
        ping_interval: int = 25,
        reconnect_max_tries: int = 0,  # 0 = 무제한
        url: Optional[str] = None,
        market_cache: MarketCache = None,
    ):
        self.api = account_manager.api  # 필요  시 KISApi도 내부에서 사용 가능
        self.tr_id = tr_id
        self.approval_key = approval_key
        self.custtype = custtype    
        
        # KIS WebSocket 기본 URL
        self.url = url or "ws://ops.koreainvestment.com:21000/ws"
        
        self.position_manager = RealPositionManager()  # 포지션 매니저 인스턴스
        self.account_manager = account_manager
        self.wsapp: Optional[websocket.WebSocketApp] = None
        self._connected_evt: threading.Event = threading.Event()
        self._stop_evt = threading.Event()
        self._reconnect_lock = threading.RLock()
        self._subscribed: Set[str] = set() # 현재 구독중인 종목 (정규화된 코드)
        self._initial_codes = set(codes) if codes else set()
        self._pending_subscribe: Set[str] = set()
        self._ping_interval = ping_interval
        self._ping_thread: Optional[threading.Thread] = None
        self._reconnect_max_tries = reconnect_max_tries
        self._reconnect_attempts = 0
        self._is_reconnecting = False
        self.market_cache = market_cache # 외부에서 주입받음
        if self.market_cache is None:
            logger.error("[WS] MarketCache가 주입되지 않았습니다. Client를 초기화할 수 없습니다.")
            raise ValueError("MarketCache is a required dependency.")
        self.max_subscriptions = config.get('system', {}).get('max_subscriptions', 40)

    def start(self):
        """WebSocket 연결 시작"""
        if not self.approval_key or len(self.approval_key) < 16:
            logger.error(f"[WS] 잘못된 approval_key: {self.approval_key}")
            return
        if not self.api.access_token:
            logger.error("[WS] access_token 없음")
            return
        
        logger.info(f"[WS] 연결 시도: url={self.url}")
        logger.info(f"[WS] approval_key={self.approval_key[:16]}...")
        logger.info(f"[WS] tr_id={self.tr_id}")
        
        self._spawn_ws()

    def stop(self):
        self._stop_evt.set()
        try:
            if self.wsapp:
                self.wsapp.close()
        except Exception:
            pass
        self._connected_evt.clear()
        logger.info("🛑 WebSocket 중지 요청 완료")

    def wait_for_connection(self, timeout: int = 10) -> bool:
        """
        WebSocket 연결이 설정될 때까지 대기합니다.
        :param timeout: 최대 대기 시간 (초)
        :return: 연결 성공 시 True, 타임아웃 시 False
        """
        logger.info(f"[WS] WebSocket 연결 대기... (최대 {timeout}초)")
        return self._connected_evt.wait(timeout)

    def subscribe(self, code: str):
        """특정 종목의 실시간 시세 구독"""
        if not code:
            return
        
        code = self._normalize(code)
        if code in self._subscribed:
            return # 이미 구독 중

        # 구독 개수 제한 체크 (안전장치)
        if len(self._subscribed) >= self.max_subscriptions:
            logger.warning(f"📡 [WS] 최대 구독 개수({self.max_subscriptions}개) 초과로 구독 불가: {code}")
            return

        if not self.is_connected:
            self._pending_subscribe.add(code)
            return
        
        msg = self._build_msg(self.tr_id, code.lstrip('A'), subscribe=True)
        if self._send_json(msg):
            self._subscribed.add(code)
            logger.info(f"📡 [WS] 구독: {code} (현재 {len(self._subscribed)}/{self.max_subscriptions})")

    def unsubscribe(self, code: str):
        """특정 종목의 실시간 시세 구독 해지"""
        if not code:
            return
        
        code = self._normalize(code)
        if code not in self._subscribed:
            return
        if not self.is_connected:
            self._subscribed.discard(code) # 로컬에서만 제거
            return
        
        msg = self._build_msg(self.tr_id, code.lstrip('A'), subscribe=False)
        if self._send_json(msg):
            self._subscribed.discard(code)
            logger.info(f"📡 [WS] 구독 해지: {code}")

    def on_open(self, ws):
        logger.info("✅ WebSocket 연결 성공")
        with self._reconnect_lock:
            self._is_reconnecting = False
        self._connected_evt.set()
        self._reconnect_attempts = 0 # 재연결 성공 시 시도 횟수 초기화
        self._start_ping_thread()
        try:
            # 초기 구독 종목들 전송
            for code in self._initial_codes:
                self.subscribe(code)
            # 재연결 시 보류된 구독 요청 처리
            for code in list(self._pending_subscribe):
                self.subscribe(code)
            self._pending_subscribe.clear()
        except Exception as e:
            logger.error(f"WS 초기/보류 구독 실패: {e}")

    def on_message(self, ws, message: str):
        """웹소켓 메시지 수신 및 처리 (KIS 실시간 시세 포맷 파싱)"""
        try:
            if not isinstance(message, str):
                return

            if message.startswith("{"):
                data = json.loads(message)
                header = data.get("header", {})
                body = data.get("body", {})
                tr_id = header.get("tr_id")

                if tr_id == "PINGPONG":
                    # logger.info("[WS] PINGPONG 수신")
                    pass
                #elif body.get("rt_cd") != "0":
                    #logger.warning(f"[WS] Error Message Received: {body}")
                elif tr_id == "H0STCNT0":  # 실시간 주식 체결가 데이터
                    output = body.get("output", {})

                    # 공식 필드명에 맞춰 파싱
                    parsed_data = {
                        'code': output.get('MKSC_SHRN_ISCD', ''),
                        'exec_time': output.get('STCK_CNTG_HOUR', ''),
                        'price': float(output.get('STCK_PRPR', 0) or 0),
                        'change_sign': output.get('PRDY_VRSS_SIGN', ''),
                        'change': float(output.get('PRDY_VRSS', 0) or 0),
                        'change_rate': float(output.get('PRDY_CTRT', 0) or 0),
                        'wghn_avrg_stck_prc': float(output.get('WGHN_AVRG_STCK_PRC', 0) or 0),
                        'open_price': float(output.get('STCK_OPRC', 0) or 0),
                        'high_price': float(output.get('STCK_HGPR', 0) or 0),
                        'low_price': float(output.get('STCK_LWPR', 0) or 0),
                        'ask_price1': float(output.get('ASKP1', 0) or 0),
                        'bid_price1': float(output.get('BIDP1', 0) or 0),
                        'exec_vol': float(output.get('CNTG_VOL', 0) or 0),
                        'acc_vol': float(output.get('ACML_VOL', 0) or 0),
                        'acc_tr_amount': float(output.get('ACML_TR_PBMN', 0) or 0),
                        'seln_cntg_csnu': int(output.get('SELN_CNTG_CSNU', 0) or 0),
                        'shnu_cntg_csnu': int(output.get('SHNU_CNTG_CSNU', 0) or 0),
                        'ntby_cntg_csnu': int(output.get('NTBY_CNTG_CSNU', 0) or 0),
                        'cttr': float(output.get('CTTR', 0) or 0),
                        'seln_cntg_smtn': float(output.get('SELN_CNTG_SMTN', 0) or 0),
                        'shnu_cntg_smtn': float(output.get('SHNU_CNTG_SMTN', 0) or 0),
                        'ccld_dvsn': output.get('CCLD_DVSN', ''),
                        'shnu_rate': float(output.get('SHNU_RATE', 0) or 0),
                        'prdy_vol_vrss_acml_vol_rate': float(output.get('PRDY_VOL_VRSS_ACML_VOL_RATE', 0) or 0),
                        'oprc_hour': output.get('OPRC_HOUR', ''),
                        'oprc_vrss_prpr_sign': output.get('OPRC_VRSS_PRPR_SIGN', ''),
                        'oprc_vrss_prpr': float(output.get('OPRC_VRSS_PRPR', 0) or 0),
                        'hgpr_hour': output.get('HGPR_HOUR', ''),
                        'hgpr_vrss_prpr_sign': output.get('HGPR_VRSS_PRPR_SIGN', ''),
                        'hgpr_vrss_prpr': float(output.get('HGPR_VRSS_PRPR', 0) or 0),
                        'lwpr_hour': output.get('LWPR_HOUR', ''),
                        'lwpr_vrss_prpr_sign': output.get('LWPR_VRSS_PRPR_SIGN', ''),
                        'lwpr_vrss_prpr': float(output.get('LWPR_VRSS_PRPR', 0) or 0),
                        'bsop_date': output.get('BSOP_DATE', ''),
                        'new_mkop_cls_code': output.get('NEW_MKOP_CLS_CODE', ''),
                        'trht_yn': output.get('TRHT_YN', ''),
                        'askp_rsqn1': float(output.get('ASKP_RSQN1', 0) or 0),
                        'bidp_rsqn1': float(output.get('BIDP_RSQN1', 0) or 0),
                        'total_askp_rsqn': float(output.get('TOTAL_ASKP_RSQN', 0) or 0),
                        'total_bidp_rsqn': float(output.get('TOTAL_BIDP_RSQN', 0) or 0),
                        'vol_tnrt': float(output.get('VOL_TNRT', 0) or 0),
                        'prdy_smns_hour_acml_vol': float(output.get('PRDY_SMNS_HOUR_ACML_VOL', 0) or 0),
                        'prdy_smns_hour_acml_vol_rate': float(output.get('PRDY_SMNS_HOUR_ACML_VOL_RATE', 0) or 0),
                        'hour_cls_code': output.get('HOUR_CLS_CODE', ''),
                        'mrkt_trtm_cls_code': output.get('MRKT_TRTM_CLS_CODE', ''),
                        'vi_stnd_prc': float(output.get('VI_STND_PRC', 0) or 0),
                    }

                    norm_code = self._normalize(parsed_data['code'])
                    self.market_cache.update_tick(norm_code, parsed_data)
                    # 1분봉 데이터 로거 (체결량 사용)
                    data_logger.add_tick(norm_code, parsed_data['price'], parsed_data['exec_vol'])
                    event_logger.log_event(parsed_data)

            elif message[0] in ['0', '1']:
                # 실시간 시세 데이터 (파이프 | 로 헤더 분리, 캐럿 ^ 으로 데이터 분리)
                # 이 부분은 JSON 파싱이 실패했을 때의 폴백으로 남겨둠
                header_parts = message.split('|')
                if len(header_parts) < 4: 
                    logger.info(f"[WS] 알 수 없는 시세 포맷 (헤더 부족): {message}")
                    return
                tr_id = header_parts[1]
                data_payload = header_parts[3]

                if tr_id == "H0STCNT0": 
                    data_fields = data_payload.split('^')
                    if len(data_fields) > 49:
                        parsed_data = {
                            'code': data_fields[0],  # MKSC_SHRN_ISCD (String)
                            'exec_time': data_fields[1],  # STCK_CNTG_HOUR (String)
                            'price': float(data_fields[2] or 0),  # STCK_PRPR (Number)
                            'change_sign': data_fields[3],  # PRDY_VRSS_SIGN (String)
                            'change': float(data_fields[4] or 0),  # PRDY_VRSS (Number)
                            'change_rate': float(data_fields[5] or 0),  # PRDY_CTRT (Number)
                            'wghn_avrg_stck_prc': float(data_fields[6] or 0),  # WGHN_AVRG_STCK_PRC (Number)
                            'open_price': float(data_fields[7] or 0),  # STCK_OPRC (Number)
                            'high_price': float(data_fields[8] or 0),  # STCK_HGPR (Number)
                            'low_price': float(data_fields[9] or 0),  # STCK_LWPR (Number)
                            'ask_price1': float(data_fields[10] or 0),  # ASKP1 (Number)
                            'bid_price1': float(data_fields[11] or 0),  # BIDP1 (Number)
                            'exec_vol': float(data_fields[12] or 0),  # CNTG_VOL (Number)
                            'acc_vol': float(data_fields[13] or 0),  # ACML_VOL (Number)
                            'acc_tr_amount': float(data_fields[14] or 0),  # ACML_TR_PBMN (Number)
                            'seln_cntg_csnu': int(data_fields[15] or 0),  # SELN_CNTG_CSNU (Number)
                            'shnu_cntg_csnu': int(data_fields[16] or 0),  # SHNU_CNTG_CSNU (Number)
                            'ntby_cntg_csnu': int(data_fields[17] or 0),  # NTBY_CNTG_CSNU (Number)
                            'cttr': float(data_fields[18] or 0),  # CTTR (Number)
                            'seln_cntg_smtn': float(data_fields[19] or 0),  # SELN_CNTG_SMTN (Number)
                            'shnu_cntg_smtn': float(data_fields[20] or 0),  # SHNU_CNTG_SMTN (Number)
                            'ccld_dvsn': data_fields[21],  # CCLD_DVSN (String)
                            'shnu_rate': float(data_fields[22] or 0),  # SHNU_RATE (Number)
                            'prdy_vol_vrss_acml_vol_rate': float(data_fields[23] or 0),  # PRDY_VOL_VRSS_ACML_VOL_RATE (Number)
                            'oprc_hour': data_fields[24],  # OPRC_HOUR (String)
                            'oprc_vrss_prpr_sign': data_fields[25],  # OPRC_VRSS_PRPR_SIGN (String)
                            'oprc_vrss_prpr': float(data_fields[26] or 0),  # OPRC_VRSS_PRPR (Number)
                            'hgpr_hour': data_fields[27],  # HGPR_HOUR (String)
                            'hgpr_vrss_prpr_sign': data_fields[28],  # HGPR_VRSS_PRPR_SIGN (String)
                            'hgpr_vrss_prpr': float(data_fields[29] or 0),  # HGPR_VRSS_PRPR (Number)
                            'lwpr_hour': data_fields[30],  # LWPR_HOUR (String)
                            'lwpr_vrss_prpr_sign': data_fields[31],  # LWPR_VRSS_PRPR_SIGN (String)
                            'lwpr_vrss_prpr': float(data_fields[32] or 0),  # LWPR_VRSS_PRPR (Number)
                            'bsop_date': data_fields[33],  # BSOP_DATE (String)
                            'new_mkop_cls_code': data_fields[34],  # NEW_MKOP_CLS_CODE (String)
                            'trht_yn': data_fields[35],  # TRHT_YN (String)
                            'askp_rsqn1': float(data_fields[36] or 0),  # ASKP_RSQN1 (Number)
                            'bidp_rsqn1': float(data_fields[37] or 0),  # BIDP_RSQN1 (Number)
                            'total_askp_rsqn': float(data_fields[38] or 0),  # TOTAL_ASKP_RSQN (Number)
                            'total_bidp_rsqn': float(data_fields[39] or 0),  # TOTAL_BIDP_RSQN (Number)
                            'vol_tnrt': float(data_fields[40] or 0),  # VOL_TNRT (Number)
                            'prdy_smns_hour_acml_vol': float(data_fields[41] or 0),  # PRDY_SMNS_HOUR_ACML_VOL (Number)
                            'prdy_smns_hour_acml_vol_rate': float(data_fields[42] or 0),  # PRDY_SMNS_HOUR_ACML_VOL_RATE (Number)
                            'hour_cls_code': data_fields[43],  # HOUR_CLS_CODE (String)
                            'mrkt_trtm_cls_code': data_fields[44],  # MRKT_TRTM_CLS_CODE (String)
                            'vi_stnd_prc': float(data_fields[45] or 0),  # VI_STND_PRC (Number)
                        }

                        norm_code = self._normalize(parsed_data['code'])
                        self.market_cache.update_tick(norm_code, parsed_data)
                        # 1분봉 데이터 로거 (체결량 사용)
                        data_logger.add_tick(norm_code, parsed_data['price'], parsed_data['exec_vol'])
                        event_logger.log_event(parsed_data)

        except Exception as e:
            # error 로그에만 위치 정보 추가
            try:
                # 우선 현재 프레임 시도
                frame = inspect.currentframe()
                if frame is not None:
                    info = inspect.getframeinfo(frame)
                    logger.error(
                        f"[WS] 메시지 처리 중 오류: {e} | 메시지: {message} "
                        f"[{info.filename}:{info.function}:{info.lineno}]"
                    )
                else:
                    # currentframe()이 None이면 trace에서 가져오기
                    stack = inspect.trace()
                    if stack and len(stack) > 1:
                        info = stack[1]
                        logger.error(
                            f"[WS] 메시지 처리 중 오류: {e} | 메시지: {message} "
                            f"[{info.filename}:{info.function}:{info.lineno}]"
                        )
                    else:
                        logger.error(f"[WS] 메시지 처리 중 오류: {e} | 메시지: {message}")
            except Exception as ee:
                logger.error(f"[WS] 메시지 처리 중 오류(로깅 중 추가 오류): {ee} | 원래 오류: {e} | 메시지: {message}")

    def on_error(self, ws, err):
        logger.error(f"🚨 WebSocket 에러: {err}")
        self._schedule_reconnect()

    def on_close(self, ws, code=None, msg=None):
        logger.info(f"WebSocket 연결 종료 code={code} msg={msg}")
        self._connected_evt.clear()
        self._schedule_reconnect()

    def _schedule_reconnect(self):
        with self._reconnect_lock:
            if self._stop_evt.is_set(): return

            if self._is_reconnecting:
                logger.debug("[WS] 재연결이 이미 진행 중입니다.")
                return
            self._is_reconnecting = True

            if self._reconnect_max_tries and self._reconnect_attempts >= self._reconnect_max_tries:
                logger.error("재연결 최대 횟수 도달 → 중지")
                self._is_reconnecting = False
                return
            
            self._reconnect_attempts += 1

            # 5번 실패마다 접속 키 갱신 시도
            if self._reconnect_attempts > 0 and self._reconnect_attempts % 5 == 0:
                logger.warning(f"[WS] 재연결 {self._reconnect_attempts}회 실패. 접속 키 갱신을 시도합니다.")
                try:
                    new_key = self.api.get_approval_key()
                    if new_key:
                        self.approval_key = new_key
                        logger.info("[WS] 새 접속 키로 갱신되었습니다.")
                    else:
                        logger.error("[WS] 새 접속 키 발급에 실패했습니다.")
                except Exception as e:
                    logger.error(f"[WS] 접속 키 갱신 중 오류: {e}")

            # 지수 백오프 적용
            delay = min(10 * (2 ** min(self._reconnect_attempts - 1, 5)), 300) # 10s, 20s, 40s, 80s, 160s, 300s (최대 5분)
            logger.info(f"[WS] {delay}s 후 재연결 시도 (#{self._reconnect_attempts})")
            threading.Thread(target=self._reconnect_after, args=(delay,), daemon=True).start()

    def _reconnect_after(self, delay: int):
        time.sleep(delay)
        if self._stop_evt.is_set():
            with self._reconnect_lock:
                self._is_reconnecting = False
            return
        try:
            # 재연결 시도 직전에 플래그를 리셋하여, 이 시도가 실패하면 다음 스케줄링이 가능하도록 함
            with self._reconnect_lock:
                self._is_reconnecting = False
            self._spawn_ws()
        except Exception as e:
            logger.error(f"재연결 시작 실패: {e}")
            self._schedule_reconnect()

    def _start_ping_thread(self):
        if self._ping_thread and self._ping_thread.is_alive(): return
        def _ping_loop():
            while not self._stop_evt.is_set():
                time.sleep(self._ping_interval)
                if not self.is_connected: return 
                try:
                    w = self.wsapp
                    if w: self._send_json({"header": {"tr_id": "PINGPONG"}})
                except Exception as e:
                    logger.debug(f"[WS] ping 실패: {e}")
        self._ping_thread = threading.Thread(target=_ping_loop, daemon=True)
        self._ping_thread.start()

    def _spawn_ws(self):
        self._connected_evt.clear()
        self.wsapp = websocket.WebSocketApp(
            self.url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        threading.Thread(target=self.wsapp.run_forever, daemon=True).start()

    def _build_msg(self, tr_id: str, tr_key: str, subscribe: bool) -> Optional[Dict[str, Any]]:
        """KIS 웹소켓 구독/해지 메시지 JSON 포맷 생성"""
        if not tr_id or not tr_key:
            logger.warning(f"[WS] Invalid message components: tr_id={tr_id}, tr_key={tr_key}")
            return None
        return {
            "header": {
                "approval_key": self.approval_key,
                "custtype": self.custtype,
                "tr_type": "1" if subscribe else "2", # 1: 구독, 2: 해지
                "content-type": "utf-8"
            },
            "body": {
                "input": {
                    "tr_id": tr_id,
                    "tr_key": tr_key
                }
            }
        }

    def _send_json(self, payload: Optional[dict]) -> bool:
        if not payload:
            return False
        w = self.wsapp
        if not w: return False
        try:
            w.send(json.dumps(payload))
            return True
        except Exception as e:
            logger.debug(f"[WS] send 실패: {e}")
            return False

    @property
    def is_connected(self) -> bool:
        return (self.wsapp is not None) and self._connected_evt.is_set()

    @staticmethod
    def _normalize(code: str) -> str:
        s = str(code).strip().upper()
        s = s.replace("-", "").replace(".", "").lstrip("A")
        # 숫자 6자리 보정
        if s.isdigit() and len(s) <= 6:
            s = s.zfill(6)
        return f"A{s}"

    def refresh_approval_key(self, new_key: str) -> None:
        try:
            if not new_key: return
            if new_key != self.approval_key:
                self.approval_key = new_key
                logger.info("[WS] approval_key 갱신 반영")
        except Exception as e:
            logger.debug(f"[WS] approval_key 갱신 처리 실패: {e}")

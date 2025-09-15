import json
import os
from time import time
from typing import Optional, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from utils.logger import logger
from datetime import datetime

def _shorten(txt: str, limit: int = 400) -> str:
    if txt is None:
        return ""
    s = str(txt).strip()
    return s[:limit] + ("..." if len(s) > limit else "")

class KISApi:
    def __init__(self, app_key, app_secret, account_no, base_url: str = "https://openapi.koreainvestment.com:9443"):
        self.app_key = app_key
        self.app_secret = app_secret
        self.account_no = account_no
        self.base_url = base_url
        self.session = requests.Session()

        # 재시도 로직 추가
        retries = Retry(total=3,
                        backoff_factor=0.5, # 0.5s, 1s, 2s 간격으로 재시도
                        status_forcelist=[429, 500, 502, 503, 504]) # 재시도할 상태 코드
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

        self.TOKEN_FILE = os.path.join("config", "token_status.json")
        self.APPROVAL_KEY_FILE = os.path.join("config", "websocket_access_key_status.json")
        os.makedirs("config", exist_ok=True)

        with open("api/api_endpoints.json", "r", encoding="utf-8") as f:
            self.endpoints = json.load(f)

        self.access_token = None
        self.approval_key = None
        
        if not self._is_token_valid():
            self.authenticate()

    def _is_token_valid(self) -> bool:
        """토큰 유효성 검사 (발급일이 오늘인지 확인)"""
        token_data = self._load_token()
        if not token_data or not token_data.get("access_token"):
            return False
        
        self.access_token = token_data.get("access_token")
        issued_at_timestamp = token_data.get("issued_at", 0)

        # 발급일자와 오늘 날짜를 비교
        issue_date = datetime.fromtimestamp(issued_at_timestamp).date()
        today_date = datetime.now().date()

        if issue_date < today_date:
            logger.warning(f"[API] 토큰 발급일({issue_date})이 오늘({today_date}) 이전이므로 재발급합니다.")
            return False
        
        logger.info("[API] 기존 토큰이 유효합니다. (오늘 발급됨)")
        return True

    def _is_approval_key_valid(self) -> bool:
        """웹소켓 접속키 유효성 검사 (발급일이 오늘인지 확인)"""
        key_data = self._load_approval_key()
        if not key_data or not key_data.get("approval_key"):
            return False

        self.approval_key = key_data.get("approval_key")
        issued_at_timestamp = key_data.get("issued_at", 0)

        # 발급일자와 오늘 날짜를 비교
        issue_date = datetime.fromtimestamp(issued_at_timestamp).date()
        today_date = datetime.now().date()

        if issue_date < today_date:
            logger.warning(f"[API] 웹소켓 접속키 발급일({issue_date})이 오늘({today_date}) 이전이므로 재발급합니다.")
            return False

        logger.info("[API] 기존 웹소켓 접속키가 유효합니다. (오늘 발급됨)")
        return True

    def set_access_token(self, token: str) -> None:
        """
        토큰 갱신 시 호출. 내부 필드 동기화.
        """
        self.access_token = token

    def request(
        self,
        key: str,
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        api_endpoints.json의 엔드포인트(key)로 호출.
        - 호출 전 토큰 유효성 검사 및 자동 갱신
        - 요청 직전 상세 정보 로깅 (헤더, 파라미터, 바디)
        - 실패 시 서버 에러 본문을 함께 로그로 남긴다.
        """
        # 1. 토큰 유효성 검사 및 자동 갱신
        if key not in ('token', 'get_approval_key') and not self._is_token_valid():
            if not self.authenticate():
                raise Exception("토큰 재발급 실패")

        # 2. 엔드포인트 정보 조회
        ep = self.endpoints[key]
        path = ep.get("url") or ep.get("path")
        if not path:
            raise KeyError(f"endpoint '{key}'에 url/path 정의가 없습니다.")
        url = self.base_url + path
        method = ep.get("method", "GET").upper()
        tr_id = ep.get("tr_id")

        # 3. 헤더 구성
        h = {
            "Content-Type": "application/json; charset=UTF-8",
            "appKey": self.app_key,
            "appSecret": self.app_secret,
            "custtype": "P",
        }
        if tr_id:
            h["tr_id"] = tr_id
        if ep.get("headers"):
            h.update(ep["headers"])
        if headers:
            h.update(headers)
        if ep.get("token_required", True):
            token_val = getattr(self, "access_token", None)
            if token_val:
                h["authorization"] = f"Bearer {token_val}"

        # 4. 요청 직전 로그 추가 (중요 정보 마스킹)
        log_h = h.copy()
        if 'appSecret' in log_h:
            log_h['appSecret'] = f"{log_h['appSecret'][:4]}..."
        if 'authorization' in log_h:
            log_h['authorization'] = f"{log_h['authorization'][:25]}..."

        # 5. API 요청 실행
        try:
            if method == "GET":
                resp = self.session.get(url, headers=h, params=params, timeout=20)
            else:
                resp = self.session.post(url, headers=h, params=params, json=body or {}, timeout=20)

            if resp.status_code >= 400:
                try:
                    j = resp.json()
                    msg = j.get("msg1") or j.get("msg") or j.get("rt_msg") or _shorten(resp.text)
                except Exception:
                    msg = _shorten(resp.text)
                logger.warning(f"[API] {key} 실패 HTTP {resp.status_code} {resp.reason} url={resp.url} msg={msg}")
                resp.raise_for_status()

            try:
                data = resp.json()
            except Exception:
                logger.warning(f"[API] {key} 응답 JSON 파싱 실패: { _shorten(resp.text) }")
                raise

            rt_cd = data.get("rt_cd")
            if rt_cd not in (None, "0"):
                msg = data.get("msg1") or data.get("msg") or data.get("rt_msg") or ""
                logger.warning(f"[API] {key} rt_cd={rt_cd} msg={msg}")

            return data

        except requests.RequestException as e:
            r = getattr(e, "response", None)
            body_msg = ""
            if r is not None:
                try:
                    j = r.json()
                    body_msg = j.get("msg1") or j.get("msg") or j.get("rt_msg") or _shorten(r.text)
                except Exception:
                    body_msg = _shorten(getattr(r, "text", "") or "")
            logger.warning(f"[API] {key} 예외: {e} body={body_msg}")
            raise

    def _save_token(self, token):
        """토큰과 발급 시간을 파일에 저장"""
        with open(self.TOKEN_FILE, "w") as f:
            json.dump({"access_token": token, "issued_at": time()}, f)
        self.access_token = token
        logger.info("[API] 새 access_token을 파일에 저장했습니다.")

    def _load_token(self):
        """파일에서 토큰을 불러옴"""
        if not os.path.exists(self.TOKEN_FILE):
            return None
        try:
            with open(self.TOKEN_FILE, "r") as f:
                data = json.load(f)
                logger.info("[API] 파일에서 access_token을 불러왔습니다.")
                return data
        except (IOError, json.JSONDecodeError) as e:
            logger.warning(f"[API] 토큰 파일 로드 실패: {e}")
            return None

    def _save_approval_key(self, key):
        """웹소켓 접속키와 발급 시간을 파일에 저장"""
        with open(self.APPROVAL_KEY_FILE, "w") as f:
            json.dump({"approval_key": key, "issued_at": time()}, f)
        self.approval_key = key
        logger.info("[API] 새 approval_key를 파일에 저장했습니다.")

    def _load_approval_key(self):
        """파일에서 웹소켓 접속키를 불러옴"""
        if not os.path.exists(self.APPROVAL_KEY_FILE):
            return None
        try:
            with open(self.APPROVAL_KEY_FILE, "r") as f:
                data = json.load(f)
                # logger.info("[API] 파일에서 approval_key를 불러왔습니다.")
                return data
        except (IOError, json.JSONDecodeError) as e:
            logger.warning(f"[API] 웹소켓 접속키 파일 로드 실패: {e}")
            return None

    def authenticate(self) -> bool:
        """KIS API 인증(토큰 발급) 요청 및 파일 저장."""
        url = f"{self.base_url}/oauth2/tokenP"
        headers = {"Content-Type": "application/json", "appKey": self.app_key, "appSecret": self.app_secret}
        body = {"grant_type": "client_credentials", "appkey": self.app_key, "appsecret": self.app_secret}
        try:
            resp = self.session.post(url, headers=headers, json=body, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            access_token = data.get("access_token")
            if access_token:
                self._save_token(access_token) # Save the new token
                logger.info("[API] 인증 성공, access_token 갱신 및 저장")
                return True
            else:
                logger.warning(f"[API] 인증 실패: {data}")
                return False
        except Exception as e:
            logger.error(f"[API] 인증 요청 중 오류: {e}")
            return False

    def get_approval_key(self) -> Optional[str]:
        """KIS API 웹소켓 접속을 위한 approval_key 발급 요청 및 파일 저장."""
        if self._is_approval_key_valid():
            return self.approval_key

        logger.info("[API] 기존 웹소켓 접속키가 유효하지 않아 재발급을 시도합니다.")
        body = {"grant_type": "client_credentials", "appkey": self.app_key, "secretkey": self.app_secret}
        try:
            data = self.request("get_approval_key", body=body)
            approval_key = data.get("approval_key")
            if approval_key:
                self._save_approval_key(approval_key)
                logger.info("[API] 웹소켓 접속 키(approval_key) 발급 성공 및 저장")
                return approval_key
            else:
                logger.warning(f"[API] 웹소켓 접속 키 발급 실패: {data}")
                return None
        except Exception as e:
            logger.error(f"[API] 웹소켓 접속 키 발급 요청 중 오류: {e}")
            return None

    def inquire_cancellable_orders(self) -> Optional[Dict[str, Any]]:
        """미체결된 정정/취소 가능 주문을 조회합니다."""
        params = {
            "CANO": self.account_no[:8],
            "ACNT_PRDT_CD": self.account_no[8:],
            "INQR_DVSN_1": "0",
            "INQR_DVSN_2": "0",
            "STRT_ODNO": "",
            "SLL_BUY_DVSN_CD": "0",
            "CCLD_YN": "N" # 미체결
        }
        try:
            return self.request("inquire_cancellable_orders", params=params)
        except Exception as e:
            logger.error(f"[API] 취소 가능 주문 조회 실패: {e}")
            return None

    def cancel_order(self, order: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """주어진 주문을 취소합니다."""
        body = {
            "CANO": self.account_no[:8],
            "ACNT_PRDT_CD": self.account_no[8:],
            "ORGN_ODNO": order.get("odno"),
            "ORD_DVSN": order.get("ord_dvsn_cd"),
            "RVSE_CNCL_DVSN_CD": "02", # 취소
            "ORD_QTY": order.get("ord_qty"),
            "ORD_UNPR": "0",
            "QTY_ALL_ORD_YN": "Y"
        }
        try:
            return self.request("order_cancel", body=body)
        except Exception as e:
            logger.error(f"[API] 주문 취소 실패 (주문번호: {order.get('odno')}): {e}")
            return None

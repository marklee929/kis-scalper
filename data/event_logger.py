import json
import os
from datetime import datetime
from collections import defaultdict
from threading import Timer, Lock
from utils.logger import logger
from typing import Dict, Any

class EventLogger:
    """
    실시간 틱 데이터를 기반으로 '시장 상태'를 분 단위로 기록하는 로거.
    - 가격대와 거래대금 티어로 종목을 분류합니다.
    - 분 단위로 어떤 종목이 어떤 그룹에 속했는지 기록합니다.
    """
    def __init__(self, save_interval_seconds: int = 600):
        self.save_interval = save_interval_seconds
        self._lock = Lock()
        # { 'MMDDHHmm': { 'code': event_data } }
        # 같은 분, 같은 종목에 대해서는 최신 데이터만 유지
        self.events_by_minute: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(dict)
        self.save_path = self._get_save_path() # 초기화 시 경로 설정
        self._load_existing_data()
        self._start_periodic_save()

    def _get_save_path(self) -> str:
        """오늘 날짜를 기반으로 저장 경로를 반환합니다."""
        today_str = datetime.now().strftime('%Y-%m-%d')
        return f'data/market_events_{today_str}.json'

    def _load_existing_data(self):
        """기존에 저장된 데이터가 있으면 불러온다."""
        # 파일 경로가 오늘 날짜와 맞는지 확인
        current_path = self._get_save_path()
        if self.save_path != current_path:
            self.events_by_minute.clear()
            self.save_path = current_path

        if not os.path.exists(self.save_path):
            return
        try:
            with self._lock:
                with open(self.save_path, 'r', encoding='utf-8') as f:
                    # defaultdict(dict)으로 복원
                    loaded_data = json.load(f)
                    self.events_by_minute = defaultdict(dict, {k: v for k, v in loaded_data.items()})
            logger.info(f"[EventLogger] 기존 이벤트 데이터 {len(self.events_by_minute)}분 로드 완료.")
        except Exception as e:
            logger.error(f"[EventLogger] 기존 이벤트 데이터 로드 실패: {e}")

    def _classify_stock(self, price: float, turnover: float) -> (str, str):
        """주가와 누적거래대금을 기반으로 종목을 분류합니다."""
        # 가격대 분류
        if price < 5000:
            price_group = 'p_under_5k'
        elif price < 10000:
            price_group = 'p_5k_10k'
        elif price < 50000:
            price_group = 'p_10k_50k'
        else:
            price_group = 'p_over_50k'
        
        # 거래대금 티어 분류 (누적 거래대금 기준)
        if turnover > 500e8: # 5000억
            turnover_tier = 'v_high'
        elif turnover > 100e8: # 1000억
            turnover_tier = 'v_mid'
        else:
            turnover_tier = 'v_low'
            
        return price_group, turnover_tier

    def log_event(self, tick_data: dict):
        """
        틱 데이터를 받아 분류하고 이벤트로 기록합니다.
        tick_data는 web_socket_manager에서 파싱된 전체 딕셔너리를 받습니다.
        """
        with self._lock:
            try:
                now = datetime.now()
                timestamp_key = now.strftime('%m%d%H%M') # 년 제외 월일시분

                code = tick_data.get('code')
                price = tick_data.get('price', 0)
                turnover = tick_data.get('acc_tr_amount', 0)
                
                if not code or price == 0: return

                price_group, turnover_tier = self._classify_stock(price, turnover)

                event_data = {
                    'price_group': price_group,
                    'turnover_tier': turnover_tier,
                    'time': now.isoformat(),
                    'price': price,
                    'high': tick_data.get('high_price', 0),
                    'low': tick_data.get('low_price', 0),
                    'exec_vol': tick_data.get('exec_vol', 0),
                    'acc_vol': tick_data.get('acc_vol', 0),
                    'change_rate': tick_data.get('change_rate', 0),
                }
                
                # 해당 분의 해당 종목 데이터를 최신으로 갱신
                self.events_by_minute[timestamp_key][code] = event_data

            except Exception as e:
                logger.error(f"[EventLogger] 이벤트 로깅 실패: {e}", exc_info=True)

    def _start_periodic_save(self):
        """주기적으로 데이터를 파일에 저장하는 타이머 시작"""
        def run():
            self.save_to_file()
            self._start_periodic_save() # 다음 저장 예약

        self.timer = Timer(self.save_interval, run)
        self.timer.daemon = True
        self.timer.start()
        logger.info(f"[EventLogger] {self.save_interval}초마다 자동 저장 기능 활성화.")

    def save_to_file(self):
        """현재까지 수집된 모든 분 단위 이벤트 데이터를 JSON 파일로 저장한다."""
        with self._lock:
            # 날짜가 바뀌었을 수 있으므로, 저장 경로를 다시 확인하고 필요하면 메모리 초기화
            current_path = self._get_save_path()
            if self.save_path != current_path:
                logger.info(f"[EventLogger] 날짜 변경 감지. 이전 날짜({self.save_path}) 데이터는 저장되었으며, 새 파일({current_path})을 시작합니다.")
                self.events_by_minute.clear()
                self.save_path = current_path

            if not self.events_by_minute:
                return

            try:
                # 디렉토리 생성
                os.makedirs(os.path.dirname(self.save_path), exist_ok=True)
                # 파일 쓰기
                with open(self.save_path, 'w', encoding='utf-8') as f:
                    json.dump(self.events_by_minute, f, ensure_ascii=False, indent=2)
                logger.info(f"[EventLogger] 이벤트 데이터 {len(self.events_by_minute)}분 분량 성공적으로 저장: {self.save_path}")
            except Exception as e:
                logger.error(f"[EventLogger] 파일 저장 실패: {e}")

    def shutdown(self):
        """시스템 종료 시 호출되어 최종 데이터를 저장합니다."""
        logger.info("[EventLogger] 종료 시 최종 저장 실행...")
        if hasattr(self, 'timer'):
            self.timer.cancel()
        self.save_to_file()

# 전역 인스턴스 생성
event_logger = EventLogger()
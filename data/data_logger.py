# filepath: c:\WORK\kis-scalper\data\data_logger.py
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict
from threading import Timer, Lock
from utils.logger import logger

class DataLogger:
    """
    실시간 틱 데이터를 수집하여 1분봉(OHLCV)으로 변환하고, 
    주기적으로 또는 프로그램 종료 시 파일에 저장하는 클래스.
    """
    def __init__(self, save_path: str = 'data/historical_ohlcv_1min.json', save_interval_seconds: int = 3600):
        self.save_path = save_path
        self.save_interval = save_interval_seconds
        self._lock = Lock()
        
        # {symbol: {open: float, high: float, low: float, close: float, volume: float, start_time: datetime}}
        self.current_bars = defaultdict(dict)
        
        # {symbol: [bar, bar, ...]}
        self.completed_bars = defaultdict(list)
        
        self._load_existing_data()
        self._start_periodic_save()

    def _load_existing_data(self):
        """기존에 저장된 데이터가 있으면 불러온다."""
        if not os.path.exists(self.save_path):
            logger.info("[DataLogger] 기존 데이터 파일 없음. 새로 시작합니다.")
            return
        try:
            with self._lock:
                with open(self.save_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data:
                        symbol = item.get('symbol')
                        bars = item.get('bars', [])
                        if symbol and bars:
                            self.completed_bars[symbol].extend(bars)
            logger.info(f"[DataLogger] 기존 데이터 {sum(len(b) for b in self.completed_bars.values())}개 로드 완료.")
        except Exception as e:
            logger.error(f"[DataLogger] 기존 데이터 로드 실패: {e}")

    def add_tick(self, symbol: str, price: float, exec_volume: float):
        """웹소켓 등에서 틱 데이터를 받아 1분봉을 업데이트한다."""
        with self._lock:
            now = datetime.now()
            current_minute = now.replace(second=0, microsecond=0)
            
            bar = self.current_bars.get(symbol)
            
            # 새로운 1분봉 시작
            if not bar or bar['start_time'] != current_minute:
                # 이전 봉이 있으면 완료된 봉으로 이동
                if bar:
                    self.completed_bars[symbol].append(bar)
                    logger.debug(f"[DataLogger] 1분봉 완성: {symbol} @ {bar['start_time'].strftime('%H:%M')} | C:{bar['close']} V:{bar['volume']}")
                
                # 새 봉 초기화
                self.current_bars[symbol] = {
                    'time': current_minute.isoformat(),
                    'open': price,
                    'high': price,
                    'low': price,
                    'close': price,
                    'volume': exec_volume,
                    'start_time': current_minute # 내부 관리용
                }
            # 기존 1분봉 업데이트
            else:
                bar['high'] = max(bar['high'], price)
                bar['low'] = min(bar['low'], price)
                bar['close'] = price
                bar['volume'] += exec_volume

    def _start_periodic_save(self):
        """주기적으로 데이터를 파일에 저장하는 타이머 시작"""
        def run():
            self.save_to_file()
            self._start_periodic_save() # 다음 저장 예약

        self.timer = Timer(self.save_interval, run)
        self.timer.daemon = True
        self.timer.start()
        logger.info(f"[DataLogger] {self.save_interval}초마다 자동 저장 기능 활성화.")

    def save_to_file(self):
        """현재까지 수집된 모든 봉 데이터를 JSON 파일로 저장한다."""
        with self._lock:
            # 저장 전, 현재 진행중인 봉(current_bars)을 완료된 봉(completed_bars)으로 이동
            # 이렇게 해야 프로그램 종료 시 마지막 봉 데이터가 유실되지 않음
            for symbol, bar in self.current_bars.items():
                if bar:
                    # 중복 추가를 피하기 위해 마지막 봉 시간 체크는 생략 (종료 시점이므로)
                    self.completed_bars[symbol].append(bar)
            self.current_bars.clear() # 이동 후 초기화

            if not self.completed_bars:
                logger.info("[DataLogger] 저장할 새로운 데이터가 없습니다.")
                return

            # 저장할 데이터 구조 생성
            output_data = []
            all_symbols = set(self.completed_bars.keys())
            
            for symbol in sorted(list(all_symbols)):
                # completed_bars에 있는 데이터만 저장
                bars_to_save = self.completed_bars[symbol]
                # 내부 관리용 start_time 필드 제거
                cleaned_bars = [{k: v for k, v in bar.items() if k != 'start_time'} for bar in bars_to_save]
                output_data.append({
                    'symbol': symbol,
                    'bars': cleaned_bars
                })

        try:
            # 디렉토리 생성
            os.makedirs(os.path.dirname(self.save_path), exist_ok=True)
            
            # 파일 쓰기
            with open(self.save_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"[DataLogger] 데이터 {sum(len(b['bars']) for b in output_data)}개 성공적으로 저장: {self.save_path}")
        except Exception as e:
            logger.error(f"[DataLogger] 파일 저장 실패: {e}")

    def shutdown(self):
        """시스템 종료 시 호출되어 최종 데이터를 저장합니다."""
        logger.info("[DataLogger] 종료 시 최종 저장 실행...")
        if hasattr(self, 'timer'):
            self.timer.cancel()
        self.save_to_file()

# 전역 인스턴스 생성
data_logger = DataLogger()

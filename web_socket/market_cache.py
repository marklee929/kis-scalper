from __future__ import annotations
from time import time
from collections import deque, defaultdict
from typing import Deque, Dict, Tuple, Optional, List, Any
import threading
import math
import pandas as pd
from datetime import datetime, timedelta
import json
import traceback

# 로깅 추가
import logging
logger = logging.getLogger(__name__)

class MarketCache:
    def __init__(self, config, position_manager=None, account_manager=None):
        self._lock = threading.RLock()
        self._MAX_WINDOW_SEC = 120
        self._MAX_POINTS = 2000
        self._series: Dict[str, Deque[Dict[str, Any]]] = {} # 원본 틱 데이터
        self._last: Dict[str, Dict[str, Any]] = {} # 마지막 틱 데이터
        self._tick_count: int = 0
        self._current_holding_data: Dict[str, Dict[str, Any]] = {} # 최신 보유/구독 종목 데이터
        self.position_manager = position_manager # 포지션 매니저 참조
        self.account_manager = account_manager
        self.config = config

        # 캔들 데이터 저장소
        self._candle_intervals = [1, 3, 5, 10] # 지원하는 캔들 주기 (분)
        self._candles: Dict[str, Dict[int, Deque[Dict[str, Any]]]] = {}

    def update_tick(self, code: str, data: Dict[str, Any], ts: Optional[float] = None) -> None:
        """
        WebSocket 수신 틱을 캐시에 반영하고 캔들 업데이트 트리거
        """
        if not code:
            return
        t = ts or time()
        with self._lock:
            dq = self._series.get(code)
            if dq is None:
                dq = deque()
                self._series[code] = dq
            
            data['timestamp'] = t
            dq.append(data)
            self._last[code] = data
            
            # 윈도우/용량 정리
            cutoff = t - self._MAX_WINDOW_SEC
            while dq and dq[0]['timestamp'] < cutoff:
                dq.popleft()
            while len(dq) > self._MAX_POINTS:
                dq.popleft()
            
            # 카운터
            self._tick_count += 1
            
            # 최신 보유/구독 종목 데이터 업데이트
            self._update_current_holding_data(code, data)

            # 캔들 업데이트 트리거
            self._update_candles(code, data)

    def _update_current_holding_data(self, code: str, latest_data: Dict[str, Any]):
        """
        보유/구독 종목의 최신 가격, 손익률, 트렌드(상승/하락/횡보) 등을 계산하여 저장
        """
        with self._lock:
            # 기본 데이터 업데이트
            holding = {
                'code': code,
                'name': latest_data.get('name', code),
                'price': latest_data.get('price', 0.0),
                'change_rate': latest_data.get('change_rate', 0.0),
                'acc_vol': latest_data.get('acc_vol', 0.0),
                'is_holding': False,
                'profit_rate': 0.0,
                'buy_price': 0.0,
                # 트렌드 정보 추가
                'trend_3': None,
                'trend_5': None,
                'trend_10': None,
            }

            # 보유 종목인 경우 손익률 계산
            if self.position_manager and code in self.position_manager.positions:
                position = self.position_manager.positions[code]
                buy_price = position['price']
                current_price = latest_data.get('price', 0.0)
                if buy_price > 0 and current_price > 0:
                    profit_rate = ((current_price - buy_price) / buy_price) * 100
                    holding['is_holding'] = True
                    holding['profit_rate'] = profit_rate
                    holding['buy_price'] = buy_price
                else:
                    logger.warning(f"[Cache] {code} 손익률 계산 불가: 매입가 또는 현재가 0")

            # 캔들 기반 트렌드 계산 (3,5,10분)
            for interval in [3, 5, 10]:
                candles = self.get_candles(code, interval)
                if len(candles) >= 2: # 최소 2개 캔들이 있어야 추세 판단 가능
                    df = pd.DataFrame(list(candles)) # deque를 list로 변환 후 DataFrame 생성
                    df.set_index('start_min', inplace=True)
                    trend = self._judge_trend(df)
                    holding[f'trend_{interval}'] = trend

            self._current_holding_data[code] = holding

    @staticmethod
    def _judge_trend(df: pd.DataFrame) -> Optional[str]:
        """
        캔들 데이터프레임을 기반으로 트렌드를 판단합니다.
        (상승, 하락, 횡보)
        """
        if len(df) < 2:
            return None
        
        # 간단한 시작/끝 가격 비교
        try:
            start_price = df['open'].iloc[0]
            end_price = df['close'].iloc[-1]
            
            if start_price == 0:
                return None
                
            change_rate = (end_price - start_price) / start_price
            
            # 변화율에 따라 트렌드 결정 (임계값은 조정 가능)
            if change_rate > 0.005: # 0.5% 이상 상승
                return '상승'
            elif change_rate < -0.005: # 0.5% 이상 하락
                return '하락'
            else:
                return '횡보'
        except (IndexError, KeyError):
            # 데이터프레임이 비어있거나 필요한 컬럼이 없는 경우
            return None

    def _update_candles(self, code: str, tick_data: Dict[str, Any]):
        """
        수신된 틱 데이터로 각 주기별 캔들 업데이트
        """
        current_time_min = math.floor(tick_data['timestamp'] / 60) # 현재 분
        price = tick_data['price']
        exec_volume = tick_data.get('exec_vol', 0) # 개별 체결량 사용

        with self._lock:
            if code not in self._candles:
                MAXLEN = self.config.get('cache', {}).get('max_candles_per_interval', 480)
                self._candles[code] = {
                    interval: deque(maxlen=MAXLEN) for interval in self._candle_intervals
                }

            for interval in self._candle_intervals:
                candles_deque = self._candles[code][interval]
                candle_start_min = math.floor(current_time_min / interval) * interval

                if not candles_deque or candles_deque[-1]['start_min'] != candle_start_min:
                    # 새 캔들 생성
                    new_candle = {
                        'start_min': candle_start_min,
                        'open': price,
                        'high': price,
                        'low': price,
                        'close': price,
                        'volume': exec_volume, # 체결량으로 시작
                        'start_ts': tick_data['timestamp'] # 캔들 시작 타임스탬프
                    }
                    candles_deque.append(new_candle)
                else:
                    # 기존 캔들 업데이트
                    current_candle = candles_deque[-1]
                    current_candle['high'] = max(current_candle['high'], price)
                    current_candle['low'] = min(current_candle['low'], price)
                    current_candle['close'] = price
                    current_candle['volume'] += exec_volume # 체결량 누적

    def get_candles(self, code: str, interval: int) -> Deque[Dict[str, Any]]:
        """
        특정 종목의 특정 주기 캔들 데이터를 반환
        """
        with self._lock:
            return self._candles.get(code, {}).get(interval, deque())

    def get_holding_data(self, code: str) -> Optional[Dict[str, Any]]:
        """
        특정 종목의 최신 보유/구독 데이터를 반환
        """
        with self._lock:
            return self._current_holding_data.get(code)

    def get_all_holding_data(self) -> List[Dict[str, Any]]:
        """
        모든 보유/구독 종목의 최신 데이터를 리스트로 반환
        """
        with self._lock:
            return list(self._current_holding_data.values())

    def get_recent_series(self, code: str, seconds: int = 60) -> Tuple[List[float], List[float], List[float]]:
        """
        최근 seconds초 구간의 (ts[], price[], vol[]) 반환
        """
        now_t = time()
        cutoff = now_t - max(1, seconds)
        with self._lock:
            dq = self._series.get(code)
            if not dq:
                return [], [], []
            ts: List[float] = []
            px: List[float] = []
            vol: List[float] = []
            for item in dq:
                if item['timestamp'] >= cutoff:
                    ts.append(item['timestamp']); px.append(item['price']); vol.append(item.get('exec_vol', 0.0))
            return ts, px, vol

    def get_recent_momentums(self, code: str, count: int = 5, interval: int = 1) -> List[float]:
        """
        최근 N개의 1분봉 모멘텀(종가 기준)을 리스트로 반환합니다.
        """
        with self._lock:
            candles = self.get_candles(code, interval) # 1분봉 캔들
            if len(candles) < 2:
                return []
            
            recent_candles = list(candles)[-(count+1):]
            
            momentums = []
            for i in range(1, len(recent_candles)):
                prev_close = recent_candles[i-1]['close']
                curr_close = recent_candles[i]['close']
                if prev_close > 0:
                    momentum = (curr_close - prev_close) / prev_close * 100
                    momentums.append(momentum)
            return momentums

    def get_last(self, code: str) -> Optional[Dict[str, Any]]:
        return self.get_quote_full(code)

    def get_quote(self, code: str) -> Optional[float]:
        with self._lock:
            v = self.get_quote_full(code)
            return v.get('price') if v else None

    def get_quote_full(self, code: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._current_holding_data.get(code)

    def reset_cache(self) -> None:
        with self._lock:
            self._series.clear()
            self._last.clear()
            self._current_holding_data.clear()
            self._tick_count = 0
            for interval_deque in self._candles.values():
                for dq in interval_deque.values():
                    dq.clear()

    def get_stats(self) -> Dict[str, int]:
        with self._lock:
            return {
                "codes": len(self._series),
                "last_count": len(self._last),
                "tick_count": self._tick_count,
            }
        
    def load_historical_data(self, file_path: str) -> None:
        """
        과거 틱 데이터를 파일에서 로드하여 캐시에 반영 (초기화 용도)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                historical_data = json.load(f)
            
            logger.info(f"[MarketCache] Loading historical tick data from {file_path}...")
            sorted_timestamps = sorted(historical_data.keys())

            for timestamp_key in sorted_timestamps:
                tick_data_at_time = historical_data[timestamp_key]
                for code, data in tick_data_at_time.items():
                    try:
                        dt_object = datetime.fromisoformat(data['time'])
                        unix_timestamp = dt_object.timestamp()
                        self.update_tick(code, data, unix_timestamp)
                    except (KeyError, ValueError) as e:
                        logger.warning(f"[MarketCache] Skipping tick due to error: {e} in {data}")
            logger.info(f"[MarketCache] Finished loading historical tick data.")

        except FileNotFoundError:
            logger.warning(f"[MarketCache] Historical tick data file not found: {file_path}. Skipping.")
        except Exception as e:
            logger.error(f"[MarketCache] Error loading historical tick data: {e}")
            logger.error(traceback.format_exc())

    def load_historical_candles(self, file_path: str) -> None:
        """
        과거 1분봉 데이터를 파일에서 로드하여 캔들 캐시에 반영 (초기화 용도)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                historical_data = json.load(f)
            
            logger.info(f"[MarketCache] Loading historical 1-min candles from {file_path}...")
            
            MAXLEN = self.config.get('cache', {}).get('max_candles_per_interval', 480)

            items_to_process = []
            if isinstance(historical_data, dict):
                items_to_process = historical_data.items()
            elif isinstance(historical_data, list):
                # Assuming format: [{"code": "A005930", "candles": [...]}, ...]
                for item in historical_data:
                    if isinstance(item, dict) and "code" in item and "candles" in item:
                        items_to_process.append((item["code"], item["candles"]))
            else:
                logger.error(f"[MarketCache] Historical candle file has unexpected format: {file_path}")
                return

            with self._lock:
                for code, candles_list in items_to_process:
                    if not isinstance(candles_list, list):
                        continue
                    
                    if code not in self._candles:
                        self._candles[code] = {
                            interval: deque(maxlen=MAXLEN) for interval in self._candle_intervals
                        }
                    
                    self._candles[code][1] = deque(candles_list, maxlen=MAXLEN)

            logger.info(f"[MarketCache] Finished loading historical 1-min candles for {len(items_to_process)} codes.")

        except FileNotFoundError:
            logger.warning(f"[MarketCache] Historical candle file not found: {file_path}. Skipping.")
        except json.JSONDecodeError as e:
            logger.error(f"[MarketCache] Error decoding JSON from {file_path}: {e}")
        except Exception as e:
            logger.error(f"[MarketCache] An unexpected error occurred while loading historical candles: {e}")
            logger.error(traceback.format_exc())

# 전역 인스턴스
market_cache = None

def init_market_cache(config, position_manager, account_manager):
    global market_cache
    market_cache = MarketCache(config, position_manager, account_manager)
    return market_cache

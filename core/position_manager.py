# filepath: c:\WORK\kis-scalper\core\position_manager.py

import time
import threading
from analytics import trade_summary

class RealPositionManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
                    cls._instance._init_singleton()
        return cls._instance

    def _init_singleton(self):
        self.positions = {}
        self._position_lock = threading.RLock()

    def get_all_positions(self):
        """스레드에 안전하게 모든 포지션의 복사본을 반환합니다."""
        with self._position_lock:
            return self.positions.copy()

    def get_position(self, code):
        with self._position_lock:
            return self.positions.get(code)

    def has_position(self, code: str) -> bool:
        """특정 종목의 포지션 보유 여부를 확인합니다."""
        with self._position_lock:
            return code in self.positions

    def add_position(self, code, shares, price, name=""):
        with self._position_lock:
            self.positions[code] = {
                'shares': shares, 'price': price, 'time': time.time(),
                'name': name or code, 'peak_price': price
            }

    def update_position_price(self, code, current_price):
        with self._position_lock:
            if code in self.positions:
                self.positions[code]['price'] = current_price
                self.positions[code]['peak_price'] = max(self.positions[code].get('peak_price', current_price), current_price)

    def close_position(self, code, quantity: int, price: float, reason: str, name: str):
        """포지션을 종료하고 거래 내역을 기록합니다. (스레드 안전성 강화)"""
        position_closed = None
        with self._position_lock:
            if code in self.positions:
                position_closed = self.positions.pop(code)

        if position_closed:
            trade_summary.record_trade(
                code=code,
                name=name,
                action='SELL',
                quantity=quantity,
                price=price,
                strategy=reason  # 매도 사유를 전략 필드에 기록
            )
        return position_closed
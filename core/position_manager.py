# filepath: c:\WORK\kis-scalper\core\position_manager.py

import time
import threading
from analytics.trade_summary import trade_summary

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

    def get_position(self, code):
        return self.positions.get(code)

    def add_position(self, code, shares, price, name=""):
        self.positions[code] = {
            'shares': shares, 'price': price, 'time': time.time(),
            'name': name or code, 'peak_price': price
        }

    def update_position_price(self, code, current_price):
        if code in self.positions:
            self.positions[code]['price'] = current_price
            self.positions[code]['peak_price'] = max(self.positions[code].get('peak_price', current_price), current_price)

    def close_position(self, code, quantity: int, price: float, reason: str, name: str):
        """포지션을 종료하고 거래 내역을 기록합니다."""
        trade_summary.record_trade(
            code=code,
            name=name,
            action='SELL',
            quantity=quantity,
            price=price,
            strategy=reason  # 매도 사유를 전략 필드에 기록
        )
        return self.positions.pop(code, None)
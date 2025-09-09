import json
import os
import logging
from threading import RLock

logger = logging.getLogger(__name__)

class BalanceManager:
    def __init__(self, filepath='config/balance.json'):
        self._lock = RLock()
        self.filepath = filepath
        self._balance = 0
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        self._load()

    def _load(self):
        with self._lock:
            try:
                if os.path.exists(self.filepath):
                    with open(self.filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self._balance = data.get('available_cash', 0)
                        logger.info(f"[Balance] 잔고 로드 성공: {self._balance:,.0f}원")
                else:
                    logger.warning(f"[Balance] 잔고 파일 없음: {self.filepath}")
            except Exception as e:
                logger.error(f"[Balance] 잔고 파일 로드 실패: {e}")

    def _save(self):
        with self._lock:
            try:
                with open(self.filepath, 'w', encoding='utf-8') as f:
                    json.dump({'available_cash': self._balance}, f, indent=2)
            except Exception as e:
                logger.error(f"[Balance] 잔고 파일 저장 실패: {e}")

    def get_balance(self) -> int:
        with self._lock:
            return self._balance

    def set_balance(self, new_balance: int):
        with self._lock:
            if isinstance(new_balance, int):
                self._balance = new_balance
                self._save()
                logger.info(f"[Balance] 잔고 업데이트: {self._balance:,.0f}원")
            else:
                logger.error(f"[Balance] 잘못된 잔고 값 타입: {type(new_balance)}")

    def spend(self, amount: int):
        with self._lock:
            if self._balance >= amount:
                self._balance -= amount
                self._save()
                logger.info(f"[Balance] 지출: {amount:,.0f}원, 남은 잔고: {self._balance:,.0f}원")
                return True
            else:
                logger.warning(f"[Balance] 잔고 부족: 요청 {amount:,} / 보유 {self._balance:,}")
                return False

    def deposit(self, amount: int):
        with self._lock:
            self._balance += amount
            self._save()
            logger.info(f"[Balance] 입금: {amount:,.0f}원, 현재 잔고: {self._balance:,.0f}원")

# 전역 잔고 관리자 인스턴스
balance_manager = BalanceManager()

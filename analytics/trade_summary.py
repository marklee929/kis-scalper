from typing import Dict, List, Optional
from datetime import datetime, timedelta, time as dt_time
from dataclasses import dataclass, asdict
import json
import os
import logging

# 로깅 설정 추가
logger = logging.getLogger(__name__)

@dataclass
class TradeRecord:
    """거래 기록"""
    timestamp: datetime
    code: str
    name: str
    action: str  # 'BUY' or 'SELL'
    quantity: int
    price: float
    amount: float
    order_id: str
    strategy: str
    weight: Optional[float] = None       # 비중 (종가매매)
    retry_count: Optional[int] = None    # 재시도 횟수

@dataclass
class DailySummary:
    """일일 서머리"""
    date: str
    total_trades: int
    buy_orders: int
    sell_orders: int
    total_volume: float
    gross_profit: float
    gross_loss: float
    net_profit: float
    win_rate: float
    largest_win: float
    largest_loss: float
    starting_balance: float
    ending_balance: float
    total_fees: float = 0.0
    real_net_profit: float = 0.0
    weighted_allocation: bool = False # 가중치 배분 전략 사용 여부
    
class TradeSummaryManager:
    """거래 서머리 관리자 (재계산 방식으로 변경)"""
    
    def __init__(self):
        self.trades: List[TradeRecord] = []
        self.starting_balance = 0.0
        self.current_balance = 0.0
        self.weighted_allocation_used_today = False # 오늘 가중치 배분 사용 여부
        
    def set_starting_balance(self, balance: float):
        """시작 잔고 설정"""
        self.starting_balance = balance
        self.current_balance = balance
        today = datetime.now().strftime('%Y-%m-%d')
        logger.info(f"[START] 시작 잔고: {balance:,.0f}원 ({today})")
        
    def record_trade(self, code: str, name: str, action: str, 
                    quantity: int, price: float, order_id: str = "", 
                    strategy: str = "manual", weight: Optional[float] = None, 
                    retry_count: Optional[int] = None):
        """거래를 기록하고 잔고만 업데이트합니다."""
        try:
            amount = quantity * price
            action_upper = action.upper()
            
            trade = TradeRecord(
                timestamp=datetime.now(),
                code=code,
                name=name,
                action=action_upper,
                quantity=quantity,
                price=price,
                amount=amount,
                order_id=order_id,
                strategy=strategy,
                weight=weight,
                retry_count=retry_count
            )
            self.trades.append(trade)
            
            if action_upper == "BUY":
                self.current_balance -= amount
            elif action_upper == "SELL":
                self.current_balance += amount
            
            log_msg = f"[TRADE] {action_upper}: {name} {quantity}주 @{price:,.0f}원"
            if weight is not None:
                log_msg += f" (비중: {weight:.2%})"
            logger.info(log_msg)
            
        except Exception as e:
            logger.error(f"[TRADE] 거래 기록 실패: {e}")
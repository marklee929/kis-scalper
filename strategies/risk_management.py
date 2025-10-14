# filepath: c:\WORK\kis-scalper\strategies\risk_management.py
from datetime import datetime, timedelta
from utils.logger import logger
from typing import Dict, Optional, List
from dataclasses import dataclass
import time

class ScalpingRiskManager:
    """
    단타 리스크 관리 클래스.

    NOTE: 이 리스크 관리자는 과거 파이프라인(score_monitor 등)에서 사용되던 규칙을 포함합니다.
    현재의 통합 트레이딩 시스템(IntegratedTradingSystem)은 자체적인 포트폴리오 레벨의 리스크 관리
    (예: 전체 평가자산 대비 손실 제한)를 사용하므로, 이 모듈의 규칙과 충돌하거나 중복될 수 있습니다.
    향후 리스크 규칙을 통합할 때 참고용으로 보존하되, 현재 시스템에서는 제한적으로 사용됩니다.
    """
    
    def __init__(self):
        self.stop_loss_pct = -0.8      # 0.8% 손절
        self.take_profit_pct = 1.2     # 1.2% 익절
        self.trailing_stop_pct = 0.3   # 트레일링 스탑
        self.max_hold_minutes = 15     # 최대 보유 시간
        self.max_daily_loss = -5.0     # 일일 최대 손실 5%
        self.max_positions = 5         # 최대 동시 포지션
        
        # 일일 통계
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.last_reset = datetime.now().date()
        
    def should_exit(self, position: Dict, current_price: float) -> Dict:
        """포지션 청산 여부 판단"""
        try:
            entry_price = position['avg_price']
            entry_time = position.get('entry_time', time.time())
            code = position.get('code', '')
            
            # 수익률 계산
            unrealized_pnl_pct = (current_price - entry_price) / entry_price * 100
            minutes_held = (time.time() - entry_time) / 60
            
            # 청산 조건 체크
            exit_reason = None
            
            # 1. 시간 기반 청산 (단타 핵심)
            if minutes_held > self.max_hold_minutes:
                exit_reason = 'time_limit'
                
            # 2. 손절선
            elif unrealized_pnl_pct <= self.stop_loss_pct:
                exit_reason = 'stop_loss'
                
            # 3. 익절선
            elif unrealized_pnl_pct >= self.take_profit_pct:
                exit_reason = 'take_profit'
                
            # 4. 트레일링 스탑 (수익 중 일부 보호)
            elif unrealized_pnl_pct > 0.5:  # 0.5% 수익 이상시 활성화
                max_profit = position.get('max_profit_pct', unrealized_pnl_pct)
                trailing_threshold = max_profit - self.trailing_stop_pct
                
                if unrealized_pnl_pct < trailing_threshold:
                    exit_reason = 'trailing_stop'
                else:
                    # 최고 수익 업데이트
                    position['max_profit_pct'] = max(max_profit, unrealized_pnl_pct)
            
            return {
                'exit': exit_reason is not None,
                'reason': exit_reason,
                'pnl_pct': unrealized_pnl_pct,
                'hold_minutes': minutes_held
            }
            
        except Exception as e:
            logger.error(f"[RISK] 청산 판단 실패: {e}")
            return {'exit': True, 'reason': 'error'}
    
    def can_open_position(self, current_positions: int, account_balance: float) -> Dict:
        """새 포지션 오픈 가능 여부"""
        # 일일 통계 리셋
        self._reset_daily_if_needed()
        
        # 체크 조건들
        checks = {
            'max_positions': current_positions < self.max_positions,
            'daily_loss_limit': self.daily_pnl > self.max_daily_loss,
            'sufficient_balance': account_balance > 100000  # 최소 잔고
        }
        
        can_open = all(checks.values())
        failed_checks = [k for k, v in checks.items() if not v]
        
        if not can_open:
            logger.warning(f"[RISK] 포지션 오픈 제한: {failed_checks}")
        
        return {
            'allowed': can_open,
            'failed_checks': failed_checks,
            'current_positions': current_positions,
            'daily_pnl': self.daily_pnl
        }
    
    def record_trade(self, pnl_pct: float):
        """거래 결과 기록"""
        self._reset_daily_if_needed()
        self.daily_pnl += pnl_pct
        self.daily_trades += 1
        
        logger.info(f"[RISK] 거래 기록: 수익률={pnl_pct:.2f}% 일일누적={self.daily_pnl:.2f}% 거래횟수={self.daily_trades}")
    
    def get_daily_stats(self) -> Dict:
        """일일 통계 조회"""
        return {
            'daily_pnl': self.daily_pnl,
            'daily_trades': self.daily_trades,
            'avg_trade': self.daily_pnl / max(self.daily_trades, 1),
            'last_reset': self.last_reset.isoformat()
        }
    
    def _reset_daily_if_needed(self):
        """날짜가 바뀌면 일일 통계 리셋"""
        today = datetime.now().date()
        if today != self.last_reset:
            logger.info(f"[RISK] 일일 통계 리셋: PnL={self.daily_pnl:.2f}% 거래={self.daily_trades}회")
            self.daily_pnl = 0.0
            self.daily_trades = 0
            self.last_reset = today

# 전역 인스턴스
risk_manager = ScalpingRiskManager()


@dataclass
class PositionSizingResult:
    """포지션 사이징 결과."""

    quantity: int
    risk_amount: float
    atr: float
    unit_size: float


class PortfolioRiskManager:
    """포트폴리오 레벨 리스크 관리 및 포지션 사이징 클래스."""

    def __init__(self, settings: Dict[str, float]):
        self.settings = settings

    def calculate_position_size(
        self,
        price: float,
        atr: float,
        portfolio_value: float,
    ) -> PositionSizingResult:
        max_position_pct = float(self.settings.get("max_position_pct", 0.02))
        stop_loss_multiplier = float(self.settings.get("stop_loss_atr_multiplier", 1.5))

        risk_amount = portfolio_value * max_position_pct
        atr_value = atr if atr > 0 else price * 0.02
        unit_risk = atr_value * stop_loss_multiplier
        if unit_risk == 0:
            return PositionSizingResult(0, risk_amount, atr_value, 0)

        quantity = int(risk_amount // unit_risk)
        if quantity <= 0:
            quantity = int((portfolio_value * 0.01) // price)

        logger.info(
            "[리스크] 포지션 크기 계산: 가격=%.2f ATR=%.2f 수량=%d",
            price,
            atr_value,
            quantity,
        )

        return PositionSizingResult(quantity, risk_amount, atr_value, unit_risk)

    def build_partial_exit_plan(self, price: float) -> List[Dict[str, float]]:
        partials = self.settings.get("partial_take_profit_levels", [])
        if not partials:
            return []

        plan = []
        for leg in partials:
            pct = float(leg.get("pct", 0))
            multiple = float(leg.get("target_multiple", 1.5))
            target = price * multiple
            plan.append({"pct": pct, "target": target})

        logger.info("[리스크] 부분 청산 계획: %s", plan)
        return plan

    def validate_stop_levels(self, price: float, stop_loss: float, take_profit: float) -> bool:
        if price <= 0 or stop_loss <= 0 or take_profit <= 0:
            return False
        if stop_loss >= price and take_profit <= price:
            return False
        return True

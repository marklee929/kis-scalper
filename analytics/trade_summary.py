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
    
class TradeSummaryManager:
    """거래 서머리 관리자 (재계산 방식으로 변경)"""
    
    def __init__(self):
        self.trades: List[TradeRecord] = []
        self.starting_balance = 0.0
        self.current_balance = 0.0
        
    def set_starting_balance(self, balance: float):
        """시작 잔고 설정"""
        self.starting_balance = balance
        self.current_balance = balance
        today = datetime.now().strftime('%Y-%m-%d')
        logger.info(f"[START] 시작 잔고: {balance:,.0f}원 ({today})")
        
    def record_trade(self, code: str, name: str, action: str, 
                    quantity: int, price: float, order_id: str = "", 
                    strategy: str = "manual"):
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
                strategy=strategy
            )
            self.trades.append(trade)
            
            if action_upper == "BUY":
                self.current_balance -= amount
            elif action_upper == "SELL":
                self.current_balance += amount
            
            logger.info(f"[TRADE] {action_upper}: {name} {quantity}주 @{price:,.0f}원")
            
        except Exception as e:
            logger.error(f"[TRADE] 거래 기록 실패: {e}")

    def get_morning_sell_summary(self) -> str:
        """오늘 아침(09:00-09:30)에 판매된 종목들의 요약을 생성합니다."""
        now = datetime.now()
        today_str = now.strftime('%Y-%m-%d')
        yesterday = now - timedelta(days=1)

        sell_window_start = now.replace(hour=9, minute=0, second=0, microsecond=0)
        sell_window_end = now.replace(hour=9, minute=30, second=0, microsecond=0)

        # 1. 오늘 아침에 매도된 거래 필터링
        morning_sells = [t for t in self.trades 
                         if t.action == 'SELL' and 
                         sell_window_start <= t.timestamp <= sell_window_end]

        if not morning_sells:
            return "(금일 시초가 매도 내역이 없습니다.)"

        # 2. 어제 매수 기록을 찾기 위한 데이터 준비
        buy_trades_last_24h = [t for t in self.trades 
                               if t.action == 'BUY' and t.timestamp >= yesterday]
        
        buy_positions = {}
        for buy in buy_trades_last_24h:
            if buy.code not in buy_positions:
                buy_positions[buy.code] = []
            buy_positions[buy.code].append(buy)

        # 3. 매도 기록을 바탕으로 손익 계산
        total_pnl = 0
        total_investment = 0
        sold_stocks_summary = []

        for sell in morning_sells:
            if sell.code in buy_positions and buy_positions[sell.code]:
                # 가장 최근의 매수 기록을 가져옴 (종가매매이므로 하나만 있어야 정상)
                buy_trade = buy_positions[sell.code].pop(0)
                
                pnl = (sell.price - buy_trade.price) * sell.quantity
                profit_rate = (sell.price / buy_trade.price - 1) * 100
                total_pnl += pnl
                total_investment += buy_trade.amount

                sold_stocks_summary.append(
                    f"- {sell.name}: {profit_rate:+.2f}% (손익: {pnl:+,}원)"
                )

        avg_profit_rate = (total_pnl / total_investment) * 100 if total_investment > 0 else 0

        # 4. 요약 텍스트 생성
        lines = [
            f"*📈 익일 종가 실현 요약 ({today_str})*",
            "="*25,
            f"- 총 실현 손익: *{total_pnl:+,}원*",
            f"- 평균 수익률: *{avg_profit_rate:+.2f}%*",
            f"- 매도 종목 수: {len(sold_stocks_summary)}개",
            "\n*매도 종목 목록:*"]
        lines.extend(sold_stocks_summary)
        
        return "\n".join(lines)

    def _calculate_summary_from_trades(self, date_str: str) -> Optional[DailySummary]:
        """메모리의 거래 목록에서 특정 날짜의 요약을 정확히 계산합니다."""
        target_trades = [t for t in self.trades if t.timestamp.strftime('%Y-%m-%d') == date_str]
        if not target_trades:
            return None

        positions = {}
        gross_profit = 0.0
        gross_loss = 0.0
        winning_trades = 0
        losing_trades = 0

        for trade_obj in target_trades:
            trade = asdict(trade_obj)
            code, action, quantity, price = trade['code'], trade['action'], trade['quantity'], trade['price']

            if action == 'BUY':
                if code not in positions:
                    positions[code] = {'quantity': 0, 'total_cost': 0}
                positions[code]['quantity'] += quantity
                positions[code]['total_cost'] += quantity * price
            
            elif action == 'SELL':
                if code not in positions or positions[code]['quantity'] == 0:
                    continue

                avg_buy_price = positions[code]['total_cost'] / positions[code]['quantity']
                sell_quantity = min(quantity, positions[code]['quantity'])
                pnl = (price - avg_buy_price) * sell_quantity
                
                if pnl > 0:
                    gross_profit += pnl
                    winning_trades += 1
                else:
                    gross_loss += pnl
                    losing_trades += 1
                
                positions[code]['quantity'] -= sell_quantity
                positions[code]['total_cost'] -= avg_buy_price * sell_quantity

        total_sell_trades = winning_trades + losing_trades
        win_rate = (winning_trades / total_sell_trades) * 100 if total_sell_trades > 0 else 0
        net_profit = gross_profit + gross_loss

        return DailySummary(
            date=date_str,
            total_trades=len(target_trades),
            buy_orders=sum(1 for t in target_trades if t.action == 'BUY'),
            sell_orders=sum(1 for t in target_trades if t.action == 'SELL'),
            total_volume=sum(t.amount for t in target_trades),
            gross_profit=gross_profit,
            gross_loss=abs(gross_loss),
            net_profit=net_profit,
            win_rate=win_rate,
            largest_win=0,
            largest_loss=0,
            starting_balance=self.starting_balance,
            ending_balance=self.current_balance
        )

    def get_summary_text(self, date_str: Optional[str] = None) -> str:
        """지정된 날짜 또는 오늘의 텍스트 서머리를 생성합니다."""
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')

        summary = self._calculate_summary_from_trades(date_str)
        if not summary:
            return f"{date_str} 거래 내역이 없습니다."

        lines = []
        lines.append(f"*거래 요약 ({summary.date})*")
        lines.append("="*20)
        lines.append(f"총 거래: {summary.total_trades}건 (매수 {summary.buy_orders}, 매도 {summary.sell_orders})")
        
        if summary.sell_orders > 0:
            lines.append(f"순손익: *{summary.net_profit:+,}원*")
            lines.append(f"승률: {summary.win_rate:.1f}%")
            lines.append(f"총수익: {summary.gross_profit:+,}원")
            lines.append(f"총손실: {summary.gross_loss:-,}원")
        
        lines.append("="*20)
        start_balance = summary.starting_balance
        end_balance = summary.ending_balance
        lines.append(f"시작잔고: {start_balance:,.0f}원")
        lines.append(f"종료잔고: {end_balance:,.0f}원")
        balance_change = end_balance - start_balance
        change_pct = (balance_change / start_balance) * 100 if start_balance > 0 else 0
        lines.append(f"잔고변화: *{balance_change:+,.0f}원 ({change_pct:+.2f}%)*")
        
        return "\n".join(lines)

    def print_shutdown_summary(self):
        """종료 시 거래 서머리 출력 (항상 재계산)"""
        summary_text = self.get_summary_text()
        
        print("\n" + "="*60)
        print("KIS 스캘핑 시스템 종료 - 거래 요약")
        print("="*60)
        print(summary_text.replace("*", ""))
        print("="*60)
        print(f"종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("거래 종료!")
        print("="*60 + "\n")
        
        logger.info("[SHUTDOWN] 거래 요약 생성 완료")
        self._save_daily_summary()

    def _save_daily_summary(self):
        """일일 서머리 파일 저장"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            filename = f"logs/trade_summary_{today}.json"
            os.makedirs("logs", exist_ok=True)
            
            summary_to_save = self._calculate_summary_from_trades(today)
            
            save_data = {
                "summary": asdict(summary_to_save) if summary_to_save else None,
                "trades": [asdict(trade) for trade in self.trades if trade.timestamp.strftime('%Y-%m-%d') == today],
                "generated_at": datetime.now().isoformat()
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"[SHUTDOWN] 거래 요약 저장: {filename}")
            
        except Exception as e:
            logger.error(f"[SHUTDOWN] 서머리 저장 실패: {e}")

# 전역 인스턴스
trade_summary = TradeSummaryManager()

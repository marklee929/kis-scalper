# filepath: c:\WORK\kis-scalper\analytics\backtesting_engine.py
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
import os
from utils.logger import logger

# --- 데이터 클래스 정의 ---

@dataclass
class Trade:
    """단일 거래 기록"""
    symbol: str
    entry_time: datetime
    exit_time: Optional[datetime]
    entry_price: float
    exit_price: Optional[float]
    shares: float
    pnl: float
    return_pct: float
    commission: float
    exit_reason: Optional[str]
    entry_signal: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PerformanceMetrics:
    """백테스트 성과 지표"""
    initial_balance: float
    final_balance: float
    total_net_pnl: float
    total_return_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    total_commission: float
    gross_profit: float
    gross_loss: float
    profit_factor: Optional[float]
    avg_trade_pnl: float
    avg_return_pct: float
    avg_win_pnl: Optional[float]
    avg_loss_pnl: Optional[float]
    max_drawdown_pct: float
    sharpe_ratio: Optional[float]
    largest_win_pnl: float
    largest_loss_pnl: float
    avg_holding_period: Optional[timedelta]

# --- 백테스팅 엔진 클래스 ---

class BacktestingEngine:
    """
    시계열 데이터를 기반으로 전략을 시뮬레이션하는 현실적인 백테스팅 엔진.
    - 실제 가격 흐름(OHLCV)에 따라 거래를 실행합니다.
    - 거래 비용(수수료, 슬리피지)을 반영합니다.
    - 상세한 성과 지표를 계산하고 리포트를 생성합니다.
    """
    
    def __init__(self, initial_balance: float = 10000000, commission_pct: float = 0.00015, slippage_pct: float = 0.0005):
        self.initial_balance = initial_balance
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct
        
        self.current_balance = initial_balance
        self.trades: List[Trade] = []
        self.equity_curve: List[Dict[str, Any]] = [{'time': None, 'balance': initial_balance}]

    def _apply_slippage(self, price: float, is_buy: bool) -> float:
        """슬리피지 적용 (매수 시 불리하게, 매도 시 유리하게)"""
        slippage = price * self.slippage_pct
        return price + slippage if is_buy else price - slippage

    def load_historical_data(self, file_path: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        시계열 데이터 로드 (JSON 형식).
        데이터는 종목 코드를 key로, OHLCV 캔들 리스트를 value로 가집니다.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            processed_data = {item['symbol']: item['bars'] for item in data if 'symbol' in item and 'bars' in item}
            
            for symbol, bars in processed_data.items():
                for bar in bars:
                    bar['time'] = datetime.fromisoformat(bar['time'])

            logger.info(f"[BACKTEST] 데이터 로드 완료: {len(processed_data)}개 종목")
            return processed_data
            
        except Exception as e:
            logger.error(f"[BACKTEST] 데이터 로드 실패: {e}")
            return {}

    def run_simulation(self, historical_data: Dict[str, List[Dict[str, Any]]], strategy_params: Dict):
        """전체 종목에 대해 시뮬레이션 실행"""
        logger.info(f"[BACKTEST] 시뮬레이션 시작: {len(historical_data)}개 종목")
        
        all_bars = []
        for symbol, bars in historical_data.items():
            for bar in bars:
                all_bars.append({'symbol': symbol, **bar})
        
        all_bars.sort(key=lambda x: x['time'])

        if not all_bars:
            logger.warning("[BACKTEST] 시뮬레이션할 데이터가 없습니다.")
            return self._calculate_performance(None)

        for bar in all_bars:
            self._simulate_step(bar['symbol'], bar, strategy_params)
            
        performance = self._calculate_performance(all_bars[-1]['time'])
        logger.info(f"[BACKTEST] 시뮬레이션 완료: 총 {performance.total_trades}건 거래, 최종 수익률 {performance.total_return_pct:.2f}%")
        return performance

    def _simulate_step(self, symbol: str, bar: Dict[str, Any], params: Dict):
        """단일 시간 단계(bar)에 대한 시뮬레이션"""
        position = next((t for t in self.trades if t.exit_price is None and t.symbol == symbol), None)

        if position:
            stop_loss_price = position.entry_price * (1 - params['stop_loss_pct'])
            take_profit_price = position.entry_price * (1 + params['take_profit_pct'])
            
            exit_reason = None
            exit_price = 0

            if bar['low'] <= stop_loss_price:
                exit_price = stop_loss_price
                exit_reason = 'STOP_LOSS'
            elif bar['high'] >= take_profit_price:
                exit_price = take_profit_price
                exit_reason = 'TAKE_PROFIT'
            elif bar['time'] - position.entry_time >= params['max_hold_period']:
                exit_price = bar['close']
                exit_reason = 'TIME_LIMIT'

            if exit_reason:
                self._execute_exit(position, bar['time'], exit_price, exit_reason)
        else:
            if self._check_entry_signal(bar, params):
                self._execute_entry(symbol, bar, params)

    def _check_entry_signal(self, bar: Dict[str, Any], params: Dict) -> bool:
        """진입 신호 체크 (사용자 정의 전략)"""
        if bar.get('volume', 0) > 10000:
            return True
        return False

    def _execute_entry(self, symbol: str, bar: Dict[str, Any], params: Dict):
        """진입 실행 (현금 흐름 로직 수정)"""
        entry_price_slippage = self._apply_slippage(bar['close'], is_buy=True)
        
        risk_per_trade = self.current_balance * params['risk_per_trade_pct']
        stop_loss_distance = entry_price_slippage * params['stop_loss_pct']
        if stop_loss_distance == 0: return
        
        shares = risk_per_trade / stop_loss_distance
        investment_amount = shares * entry_price_slippage
        
        if investment_amount > self.current_balance * params['max_investment_pct']:
            investment_amount = self.current_balance * params['max_investment_pct']
            shares = investment_amount / entry_price_slippage

        commission = investment_amount * self.commission_pct
        if investment_amount + commission > self.current_balance:
            return

        self.current_balance -= (investment_amount + commission)

        new_trade = Trade(
            symbol=symbol,
            entry_time=bar['time'],
            exit_time=None,
            entry_price=entry_price_slippage,
            exit_price=None,
            shares=shares,
            pnl=0,
            return_pct=0,
            commission=commission,
            exit_reason=None
        )
        self.trades.append(new_trade)
        self.equity_curve.append({'time': bar['time'], 'balance': self.current_balance})
        logger.debug(f"진입: {symbol} @ {entry_price_slippage:.2f}, 수량: {shares:.2f}")

    def _execute_exit(self, trade: Trade, exit_time: datetime, exit_price: float, reason: str):
        """청산 실행 (현금 흐름 로직 수정)"""
        exit_price_slippage = self._apply_slippage(exit_price, is_buy=False)
        
        investment_amount = trade.shares * trade.entry_price
        exit_value = trade.shares * exit_price_slippage
        exit_commission = exit_value * self.commission_pct
        
        pnl = (exit_value - exit_commission) - investment_amount
        
        self.current_balance += (exit_value - exit_commission)
        
        trade.exit_time = exit_time
        trade.exit_price = exit_price_slippage
        trade.pnl = pnl
        trade.return_pct = (pnl / investment_amount) * 100 if investment_amount != 0 else 0
        trade.commission += exit_commission
        trade.exit_reason = reason
        
        self.equity_curve.append({'time': exit_time, 'balance': self.current_balance})
        logger.debug(f"청산: {trade.symbol} @ {exit_price_slippage:.2f}, 수익: {pnl:.2f}, 이유: {reason}")

    def _calculate_performance(self, end_date: Optional[datetime]) -> PerformanceMetrics:
        """성과 지표 계산"""
        if not self.trades:
            logger.warning("[BACKTEST] 거래가 없어 성과를 계산할 수 없습니다.")
            return PerformanceMetrics(
                initial_balance=self.initial_balance, final_balance=self.current_balance,
                total_net_pnl=0, total_return_pct=0, total_trades=0, winning_trades=0,
                losing_trades=0, win_rate_pct=0, total_commission=0, gross_profit=0,
                gross_loss=0, profit_factor=None, avg_trade_pnl=0, avg_return_pct=0,
                avg_win_pnl=None, avg_loss_pnl=None, max_drawdown_pct=0, sharpe_ratio=None,
                largest_win_pnl=0, largest_loss_pnl=0, avg_holding_period=None
            )

        pnls = [t.pnl for t in self.trades]
        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl <= 0]

        equity_df = pd.DataFrame(self.equity_curve).set_index('time')
        equity_df['drawdown'] = equity_df['balance'] / equity_df['balance'].cummax() - 1
        max_drawdown_pct = equity_df['drawdown'].min() * 100

        if not equity_df['balance'].pct_change().std() == 0:
            sharpe_ratio = np.sqrt(252) * equity_df['balance'].pct_change().mean() / equity_df['balance'].pct_change().std()
        else:
            sharpe_ratio = 0

        total_pnl = self.current_balance - self.initial_balance
        gross_profit = sum(t.pnl for t in winning_trades)
        gross_loss = sum(t.pnl for t in losing_trades)

        holding_periods = [t.exit_time - t.entry_time for t in self.trades if t.exit_time]
        avg_holding = sum(holding_periods, timedelta(0)) / len(holding_periods) if holding_periods else None

        return PerformanceMetrics(
            initial_balance=self.initial_balance,
            final_balance=self.current_balance,
            total_net_pnl=total_pnl,
            total_return_pct=(total_pnl / self.initial_balance) * 100,
            total_trades=len(self.trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate_pct=(len(winning_trades) / len(self.trades) * 100) if self.trades else 0,
            total_commission=sum(t.commission for t in self.trades),
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            profit_factor=abs(gross_profit / gross_loss) if gross_loss != 0 else None,
            avg_trade_pnl=np.mean(pnls) if pnls else 0,
            avg_return_pct=np.mean([t.return_pct for t in self.trades]) if self.trades else 0,
            avg_win_pnl=np.mean([t.pnl for t in winning_trades]) if winning_trades else None,
            avg_loss_pnl=np.mean([t.pnl for t in losing_trades]) if losing_trades else None,
            max_drawdown_pct=max_drawdown_pct,
            sharpe_ratio=sharpe_ratio,
            largest_win_pnl=max(pnls) if pnls else 0,
            largest_loss_pnl=min(pnls) if pnls else 0,
            avg_holding_period=avg_holding
        )

    def generate_report(self, performance: PerformanceMetrics) -> str:
        """상세 리포트 생성"""
        start_time = self.equity_curve[0]['time'] or (self.trades[0].entry_time if self.trades else 'N/A')
        end_time = self.equity_curve[-1]['time'] or 'N/A'
        
        sharpe_text = f"{performance.sharpe_ratio:.2f}" if performance.sharpe_ratio is not None else "N/A"
        pf_text = f"{performance.profit_factor:.2f}" if performance.profit_factor is not None else "N/A"
        avg_win_text = f"{performance.avg_win_pnl:,.0f}" if performance.avg_win_pnl is not None else "N/A"
        avg_loss_text = f"{performance.avg_loss_pnl:,.0f}" if performance.avg_loss_pnl is not None else "N/A"

        report = f"""
        --- 백테스트 결과 리포트 ---
        시뮬레이션 기간: {start_time} ~ {end_time}

        [성과 요약]
        - 초기 자본: {performance.initial_balance:,.0f} 원
        - 최종 자본: {performance.final_balance:,.0f} 원
        - 총 순손익: {performance.total_net_pnl:,.0f} 원
        - 총 수익률: {performance.total_return_pct:.2f} %
        - 최대 낙폭(MDD): {performance.max_drawdown_pct:.2f} %
        - 샤프 비율: {sharpe_text}

        [거래 분석]
        - 총 거래: {performance.total_trades} 건
        - 승리: {performance.winning_trades} 건
        - 패배: {performance.losing_trades} 건
        - 승률: {performance.win_rate_pct:.2f} %
        - 손익비: {pf_text}
        - 총 수수료: {performance.total_commission:,.0f} 원

        [손익 상세]
        - 평균 손익 (거래당): {performance.avg_trade_pnl:,.0f} 원 ({performance.avg_return_pct:.2f} %)
        - 평균 이익 (승리 시): {avg_win_text} 원
        - 평균 손실 (패배 시): {avg_loss_text} 원
        - 최대 이익 (단일 거래): {performance.largest_win_pnl:,.0f} 원
        - 최대 손실 (단일 거래): {performance.largest_loss_pnl:,.0f} 원
        
        [보유 기간]
        - 평균 보유 시간: {str(performance.avg_holding_period)}
        """
        return report

    def save_results(self, performance: PerformanceMetrics, report: str):
        """결과를 JSON과 TXT 파일로 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = "logs/backtests"
        os.makedirs(output_dir, exist_ok=True)

        report_path = os.path.join(output_dir, f"report_{timestamp}.txt")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        result_data = {
            'performance_summary': asdict(performance),
            'trades': [asdict(trade) for trade in self.trades]
        }
        json_path = os.path.join(output_dir, f"trades_{timestamp}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2, default=str)
            
        logger.info(f"[BACKTEST] 리포트 및 거래 내역 저장 완료: {output_dir}")

# 전역 인스턴스 생성
backtest_engine = BacktestingEngine()
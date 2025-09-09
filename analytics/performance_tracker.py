# filepath: c:\WORK\kis-scalper\analytics\performance_tracker.py
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json
import os
from dataclasses import dataclass, asdict
from utils.logger import logger

@dataclass
class RealTimeMetrics:
    """실시간 성과 지표"""
    timestamp: datetime
    account_balance: float
    open_positions: int
    daily_pnl: float
    daily_trades: int
    win_rate: float
    current_drawdown: float

class PerformanceTracker:
    """실시간 성과 추적기"""
    
    def __init__(self):
        self.metrics_history: List[RealTimeMetrics] = []
        self.daily_snapshots: Dict[str, RealTimeMetrics] = {}
        self.alerts_sent: List[str] = []
        
    def record_metrics(self, 
                      account_balance: float,
                      open_positions: int,
                      daily_pnl: float,
                      daily_trades: int,
                      win_rate: float):
        """실시간 지표 기록"""
        try:
            now = datetime.now()
            
            # 현재 낙폭 계산
            current_drawdown = self._calculate_current_drawdown(daily_pnl)
            
            metrics = RealTimeMetrics(
                timestamp=now,
                account_balance=account_balance,
                open_positions=open_positions,
                daily_pnl=daily_pnl,
                daily_trades=daily_trades,
                win_rate=win_rate,
                current_drawdown=current_drawdown
            )
            
            self.metrics_history.append(metrics)
            
            # 일일 스냅샷 저장
            date_key = now.strftime("%Y-%m-%d")
            self.daily_snapshots[date_key] = metrics
            
            # 알림 체크
            self._check_alerts(metrics)
            
            # 로그 (5분마다)
            if len(self.metrics_history) % 5 == 0:
                logger.info(f"📊 [PERF] 잔고={account_balance:,.0f} "
                           f"포지션={open_positions}개 "
                           f"일일손익={daily_pnl:.2f}% "
                           f"승률={win_rate:.1f}%")
                           
        except Exception as e:
            logger.error(f"[PERF] 지표 기록 실패: {e}")
    
    def _calculate_current_drawdown(self, daily_pnl: float) -> float:
        """현재 낙폭 계산"""
        try:
            if not self.metrics_history:
                return 0.0
            
            # 최근 30분간 최고점 대비 현재 낙폭
            recent_history = self.metrics_history[-30:]  # 30개 기록
            if not recent_history:
                return 0.0
                
            max_pnl = max(m.daily_pnl for m in recent_history)
            return daily_pnl - max_pnl
            
        except Exception as e:
            logger.debug(f"[PERF] 낙폭 계산 실패: {e}")
            return 0.0
    
    def _check_alerts(self, metrics: RealTimeMetrics):
        """알림 조건 체크"""
        try:
            alerts = []
            
            # 1. 과도한 손실 알림
            if metrics.daily_pnl <= -3.0:
                alert_key = f"daily_loss_{datetime.now().strftime('%Y%m%d')}"
                if alert_key not in self.alerts_sent:
                    alerts.append(f"🚨 일일 손실 {metrics.daily_pnl:.1f}% 달성")
                    self.alerts_sent.append(alert_key)
            
            # 2. 낙폭 알림
            if metrics.current_drawdown <= -2.0:
                alert_key = f"drawdown_{datetime.now().strftime('%Y%m%d_%H')}"
                if alert_key not in self.alerts_sent:
                    alerts.append(f"📉 낙폭 {metrics.current_drawdown:.1f}% 발생")
                    self.alerts_sent.append(alert_key)
            
            # 3. 과도한 포지션 알림
            if metrics.open_positions >= 8:
                alert_key = f"positions_{datetime.now().strftime('%Y%m%d_%H')}"
                if alert_key not in self.alerts_sent:
                    alerts.append(f"⚠️ 포지션 {metrics.open_positions}개 과다")
                    self.alerts_sent.append(alert_key)
            
            # 4. 좋은 성과 알림
            if metrics.daily_pnl >= 5.0:
                alert_key = f"good_perf_{datetime.now().strftime('%Y%m%d')}"
                if alert_key not in self.alerts_sent:
                    alerts.append(f"🎉 일일 수익 {metrics.daily_pnl:.1f}% 달성!")
                    self.alerts_sent.append(alert_key)
            
            # 알림 로그
            for alert in alerts:
                logger.warning(f"[ALERT] {alert}")
                
        except Exception as e:
            logger.debug(f"[PERF] 알림 체크 실패: {e}")
    
    def get_daily_summary(self, date: Optional[str] = None) -> Dict:
        """일일 요약"""
        try:
            if not date:
                date = datetime.now().strftime("%Y-%m-%d")
            
            if date not in self.daily_snapshots:
                return {}
            
            snapshot = self.daily_snapshots[date]
            
            return {
                'date': date,
                'final_balance': snapshot.account_balance,
                'daily_pnl': snapshot.daily_pnl,
                'total_trades': snapshot.daily_trades,
                'win_rate': snapshot.win_rate,
                'max_drawdown': snapshot.current_drawdown,
                'max_positions': max((m.open_positions for m in self.metrics_history 
                                     if m.timestamp.strftime("%Y-%m-%d") == date), default=0)
            }
            
        except Exception as e:
            logger.error(f"[PERF] 일일 요약 실패: {e}")
            return {}
    
    def save_daily_report(self, date: Optional[str] = None):
        """일일 리포트 저장"""
        try:
            if not date:
                date = datetime.now().strftime("%Y-%m-%d")
            
            summary = self.get_daily_summary(date)
            if not summary:
                return
            
            # 리포트 생성
            report = f"""
📊 일일 거래 성과 리포트 - {date}
{'='*40}

💰 계좌 현황:
• 최종 잔고: {summary['final_balance']:,.0f}원
• 일일 손익: {summary['daily_pnl']:.2f}%
• 최대 낙폭: {summary['max_drawdown']:.2f}%

📈 거래 현황:
• 총 거래: {summary['total_trades']}건
• 승률: {summary['win_rate']:.1f}%
• 최대 동시 포지션: {summary['max_positions']}개

⏰ 생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            # 파일 저장
            filename = f"logs/daily_report_{date}.txt"
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report)
            
            logger.info(f"[PERF] 일일 리포트 저장: {filename}")
            
        except Exception as e:
            logger.error(f"[PERF] 일일 리포트 저장 실패: {e}")

# 전역 인스턴스
performance_tracker = PerformanceTracker()
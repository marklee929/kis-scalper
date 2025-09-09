# filepath: c:\WORK\kis-scalper\run_backtest.py
from analytics.backtesting_engine import BacktestingEngine
from utils.logger import logger
from datetime import timedelta
import sys
import os

def main():
    """현실적인 백테스팅 엔진을 사용하여 전략을 실행합니다."""
    logger.info("--- 📈 현실적인 백테스팅 엔진 시작 ---")

    # --- 1. 백테스트 설정 ---
    
    # 사용할 데이터 파일
    # 중요: 이 파일은 OHLCV 시계열 데이터를 포함해야 합니다.
    # 형식: [{'symbol': '005930', 'bars': [{'time': '...', 'open': ..., 'high': ..., 'low': ..., 'close': ..., 'volume': ...}, ...]}, ...]
    data_file = "data/historical_ohlcv_1min.json" 
    
    # 테스트할 전략의 파라미터
    strategy_params = {
        'stop_loss_pct': 0.008,         # 0.8% 손절
        'take_profit_pct': 0.015,       # 1.5% 익절
        'max_hold_period': timedelta(minutes=30), # 최대 30분 보유
        'risk_per_trade_pct': 0.02,     # 거래당 리스크 (계좌 대비)
        'max_investment_pct': 0.20      # 최대 투자 비중 (계좌 대비)
    }

    # 엔진 초기화 (초기자본, 수수료 등 설정)
    # 전역 인스턴스 대신 새로운 인스턴스를 생성하여 테스트의 독립성을 보장합니다.
    engine = BacktestingEngine(
        initial_balance=10000000, 
        commission_pct=0.00015, 
        slippage_pct=0.0005
    )

    # --- 2. 데이터 로드 ---
    if not os.path.exists(data_file):
        logger.error(f"백테스트 데이터 파일을 찾을 수 없습니다: {data_file}")
        logger.error("데이터 파일은 'symbol'과 OHLCV 'bars' 리스트를 포함한 JSON 형식이어야 합니다.")
        logger.info("예시: [{'symbol': '005930', 'bars': [{'time': '2025-08-18T09:00:00', 'open': 75000, ...}, ...]}, ...]")
        return
    
    historical_data = engine.load_historical_data(data_file)
    if not historical_data:
        logger.error("데이터 로드에 실패했거나 데이터가 비어있습니다.")
        return

    # --- 3. 시뮬레이션 실행 ---
    performance = engine.run_simulation(historical_data, strategy_params)
    if not performance:
        logger.error("시뮬레이션 실행 중 오류가 발생했습니다.")
        return

    # --- 4. 결과 리포트 생성 및 저장 ---
    report = engine.generate_report(performance)
    print(report) # 콘솔에 리포트 출력
    
    engine.save_results(performance, report)

    logger.info("--- 🏁 백테스팅 완료 ---")


if __name__ == "__main__":
    main()

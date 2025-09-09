import json
import os
import logging
from logging.handlers import TimedRotatingFileHandler
import sys
from datetime import datetime, date
from pathlib import Path

import pandas as pd

# 알림 채널을 notifier로 일원화
# from utils.notifier import notifier # 순환 참조 방지를 위해 함수 내에서 임포트

def setup_logger():
    """
    로그 로테이션 기능이 포함된 로거를 설정합니다.
    - 매일 자정 로그 파일을 교체합니다.
    - 최대 7일치의 로그 파일을 보관합니다.
    - 콘솔과 파일에 동시에 로그를 출력합니다.
    """
    LOG_DIR = Path("logs")
    LOG_DIR.mkdir(exist_ok=True)

    logger = logging.getLogger("trading")
    
    if logger.hasHandlers():
        logger.handlers.clear()

    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)-5s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = TimedRotatingFileHandler(
        LOG_DIR / "app.log", when="midnight", interval=1, backupCount=7, encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger

logger = setup_logger()

def log_trade(trade_data: dict):
    """
    딕셔너리 형태의 트레이드 로그를 기록합니다.
    """
    log_path = os.path.join("logs", f"trades_{datetime.today().date()}.json")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    try:
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = []

        data.append(trade_data)
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    except Exception as e:
        print(f"[❌LOG_ERROR] 로그 저장 실패: {e}")

def append_to_current_positions(code, price, qty):
    """현재 포지션 파일에 보유 종목을 업데이트."""
    path = Path("logs") / "current_positions.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = []

    exists = next((x for x in data if x["code"] == code), None)
    if exists:
        exists["quantity"] += qty
        logger.debug(f"Position updated: {code} += {qty} (total {exists['quantity']})")
    else:
        data.append({"code": code, "buy_price": price, "quantity": qty})
        logger.debug(f"Position added: {code} {qty} @ {price}")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def append_sell_log(code, quantity, buy_price, sell_price, profit_rate):
    """매도 거래를 JSON 파일에 저장하고 로그에 기록."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    log_file = Path("logs") / f"trades_{date_str}.json"
    if log_file.exists():
        with open(log_file, "r", encoding="utf-8") as f:
            logs = json.load(f)
    else:
        logs = []

    entry = {
        "code": code,
        "quantity": quantity,
        "buy_price": buy_price,
        "sell_price": sell_price,
        "profit_rate": round(profit_rate * 100, 2),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    logs.append(entry)
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

    logger.info(f"Sell logged: {code} {quantity} @ {sell_price} ({round(profit_rate*100,2)}%)")

def summarize_day_trades(trades=None):
    from utils.notifier import notifier
    today = datetime.now().strftime("%Y-%m-%d")
    trade_log_path = Path("logs") / f"trades_{today}.json"
    summary_path = Path("logs") / f"summary_{today}.json"

    if not trade_log_path.exists():
        logger.warning(f"No trades to summarize for {today}")
        return

    with open(trade_log_path, encoding="utf-8") as f:
        trades = json.load(f)

    total_profit_value = 0
    total_invested = 0
    max_profit = -9999
    min_profit = 9999
    max_code = ""
    min_code = ""
    total_qty = 0

    for trade in trades:
        buy_price = trade.get("buy_price", 0)
        sell_price = trade.get("sell_price", 0)
        qty = trade.get("quantity", 0)
        profit_rate = trade.get("profit_rate", 0)

        invested = buy_price * qty
        realized = (sell_price - buy_price) * qty

        total_invested += invested
        total_profit_value += realized
        total_qty += qty

        if profit_rate > max_profit:
            max_profit = profit_rate
            max_code = trade["code"]
        if profit_rate < min_profit:
            min_profit = profit_rate
            min_code = trade["code"]

    avg_profit_rate = round((total_profit_value / total_invested) * 100, 2) if total_invested else 0

    summary = {
        "date": today,
        "total_trades": len(trades),
        "average_profit_weighted": avg_profit_rate,
        "max_profit": round(max_profit, 2),
        "max_profit_code": max_code,
        "min_profit": round(min_profit, 2),
        "min_profit_code": min_code,
        "total_profit_sum": int(total_profit_value),
        "total_invested": int(total_invested)
    }

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    logger.info(f"Day summary saved → {summary_path}")
    
    # notifier를 사용하여 텔레그램 요약 전송
    summary_text = (
        f"📊 *일일 거래 요약 ({summary['date']})*\n"
        f"총 거래: {summary['total_trades']}건\n"
        f"총 투자금: {summary['total_invested']:,}원\n"
        f"총 실현손익: {summary['total_profit_sum']:,}원\n"
        f"가중 평균 수익률: {summary['average_profit_weighted']:.2f}%\n"
        f"최고 수익: {summary['max_profit_code']} ({summary['max_profit']:.2f}%)\n"
        f"최저 수익: {summary['min_profit_code']} ({summary['min_profit']:.2f}%)"
    )
    notifier.send_message(summary_text)

def save_daily_summary():
    from utils.notifier import notifier
    today = datetime.now().strftime("%Y-%m-%d")
    log_path = Path(f"logs/trades_{today}.json")
    output_path = Path(f"data/summary_{today}.xlsx")
    Path("data").mkdir(exist_ok=True)

    if not log_path.exists():
        logger.error("저장 실패: 거래 로그 파일이 없습니다.")
        return

    with open(log_path, encoding="utf-8") as f:
        logs = json.load(f)

    df = pd.DataFrame(logs)
    try:
        df.to_excel(output_path, index=False)
        logger.info(f"✅ 엑셀 저장 완료: {output_path}")
    except Exception as e:
        logger.error(f"엑셀 저장 실패: {e}")

    # notifier를 사용하여 텔레그램으로 거래 기록 전송
    notifier.send_message(
        f"📦 *자동매매 종료*\n📝 {date.today()} 거래 요약 ({len(logs)}건)"
    )

    text_blocks = []
    current_block = ""
    for entry in logs:
        line = json.dumps(entry, ensure_ascii=False)
        if len(current_block) + len(line) + 1 > 4000:
            text_blocks.append(current_block)
            current_block = ""
        current_block += line + "\n"
    if current_block:
        text_blocks.append(current_block)

    for idx, block in enumerate(text_blocks, start=1):
        message_block = f"```json\n[{idx}/{len(text_blocks)}]\n{block.strip()}\n```"
        notifier.send_message(message_block)

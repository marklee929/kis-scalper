from datetime import datetime, timedelta
from typing import Dict, Optional, List
import logging
import numpy as np

from api.account_manager import KISAccountManager
from core.position_manager import RealPositionManager
from strategies.swing_screener import is_etf_like

logger = logging.getLogger(__name__)

class NewsDeduper:
    def __init__(self, window_sec=300):
        self.window = timedelta(seconds=window_sec)
        self.last: Dict[str, datetime] = {}

    def allow(self, code: str, now: datetime) -> bool:
        t = self.last.get(code)
        if t and now - t < self.window:
            return False
        self.last[code] = now
        return True

news_deduper = NewsDeduper(window_sec=300)

def match_stock_symbol(news_item: Dict, swing_candidates: Dict) -> Optional[str]:
    query = news_item.get('query')
    if not query: return None
    for code, stock_info in swing_candidates.items():
        if stock_info.get('name') == query:
            return code
    return None

def check_reversal_signals(code: str, market_cache) -> bool:
    """하락세가 멈추고 반등 신호가 나오는지 확인합니다."""
    try:
        ohlcv_5m = market_cache.get_candles(code, interval=5)
        if not ohlcv_5m or len(ohlcv_5m) < 6:
            logger.debug(f"[{code}] 반등 신호 체크: 5분봉 데이터 부족 (수집된 봉: {len(ohlcv_5m) if ohlcv_5m else 0}개)")
            return False

        last_candle = ohlcv_5m[-1]
        prev_candle = ohlcv_5m[-2]
        recent_4_candles = ohlcv_5m[-6:-2]

        higher_low = last_candle['low'] > prev_candle['low']
        consecutive_green = (last_candle['close'] > last_candle['open']) and \
                            (prev_candle['close'] > prev_candle['open'])
        avg_volume = np.mean([c['volume'] for c in recent_4_candles])
        volume_spike = last_candle['volume'] > (avg_volume * 2)

        if higher_low and consecutive_green and volume_spike:
            logger.info(f"✅ [{code}] 반등 신호 포착: 저점 상승, 연속 양봉, 거래량 증가 조건을 모두 만족했습니다.")
            return True
        else:
            logger.debug(f"[{code}] 반등 신호 없음: 저점상승({higher_low}), 연속양봉({consecutive_green}), 거래량증가({volume_spike})")
            return False

    except Exception as e:
        logger.error(f"[{code}] 반등 신호 체크 중 오류: {e}", exc_info=True)
        return False

def on_news_event(
    news_item: Dict,
    swing_candidates: Dict, 
    broker: KISAccountManager, 
    position_mgr: RealPositionManager, 
    cfg: Dict,
    now_fn=datetime.now
):
    published_at = news_item.get("published_at")
    if not published_at or (now_fn() - published_at).total_seconds() > 600:
        return

    code = match_stock_symbol(news_item, swing_candidates)
    if not code: return

    name = swing_candidates.get(code, {}).get("name", "")
    if is_etf_like(name, code, cfg.get("trading", {})):
        return

    if position_mgr.has_position(code) or broker.has_open_order(code):
        logger.info(f"[NEWS-HANDLER] 이미 보유 또는 미체결 주문이 있어 매수 건너뜀: {name}({code})")
        return

    now = now_fn()
    if not news_deduper.allow(code, now):
        return

    if not check_reversal_signals(code, broker.market_cache):
        logger.debug(f"[{code}] 뉴스는 발생했으나, 반등 신호가 없어 매수를 보류합니다.")
        return

    trading_config = cfg.get('trading', {})
    buy_qty = trading_config.get('swing_buy_qty', 1)

    quote_info = broker.market_cache.get_quote_full(code)
    if not quote_info or not quote_info.get('ask_price', 0) > 0:
        logger.warning(f"[NEWS-BUY] {name} ({code}) 호가 정보가 없어 매수를 건너뜁니다.")
        return

    best_ask = quote_info.get('ask_price', 0)

    if best_ask > 0:
        limit_px = round(best_ask * 1.001, 2)
        logger.info(f"[NEWS-BUY] 뉴스와 반등 신호 확인, 매수 트리거: {name}({code}), 수량: {buy_qty}, 지정가: {limit_px}")
        
        res = broker.place_buy_with_limit_then_market(
            stock_code=code,
            quantity=buy_qty,
            limit_price=limit_px,
        )
        
        if res.ok and res.filled_qty > 0:
            logger.info(f"[NEWS-BUY] 매수 성공: {name}({code}), 체결 수량: {res.filled_qty}, 메시지: {res.msg}")
            position_mgr.add_position(code, res.filled_qty, best_ask, name)
        else:
            logger.error(f"[NEWS-BUY] 매수 최종 실패: {name}({code}), 메시지: {res.msg}")
    else:
        logger.warning(f"[NEWS-BUY] {name}({code}) 최우선 매도 호가를 찾을 수 없어 매수를 건너뜁니다.")
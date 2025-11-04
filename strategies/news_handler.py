from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, Optional, List, Callable
import logging
import numpy as np

from api.account_manager import KISAccountManager
from core.position_manager import RealPositionManager
from strategies.swing_screener import is_etf_like

logger = logging.getLogger(__name__)


class NewsDeduper:
    def __init__(self, window_sec: int = 300) -> None:
        self.window = timedelta(seconds=window_sec)
        self.last_seen: Dict[str, datetime] = {}

    def allow(self, code: str, now: datetime) -> bool:
        previous = self.last_seen.get(code)
        if previous and now - previous < self.window:
            return False
        self.last_seen[code] = now
        return True


news_deduper = NewsDeduper(window_sec=300)


def match_stock_symbol(news_item: Dict, swing_candidates: Dict) -> Optional[str]:
    query = news_item.get("query")
    if not query:
        return None

    for code, stock_info in swing_candidates.items():
        if stock_info.get("name") == query:
            return code
    return None


def check_reversal_signals(code: str, market_cache) -> bool:
    """간단한 반등 조건(고가·저가, 연속 양봉, 거래량)을 확인한다."""
    try:
        candles: List[Dict] = market_cache.get_candles(code, interval=5)
        if not candles or len(candles) < 6:
            logger.debug(
                "[%s] 반등 신호 미검출: 5분봉 데이터 부족 (수집=%s)",
                code,
                len(candles) if candles else 0,
            )
            return False

        last_candle = candles[-1]
        prev_candle = candles[-2]
        recent_window = candles[-6:-2]

        higher_low = last_candle["low"] > prev_candle["low"]
        consecutive_green = (
            last_candle["close"] > last_candle["open"]
            and prev_candle["close"] > prev_candle["open"]
        )
        avg_volume = np.mean([c["volume"] for c in recent_window])
        volume_spike = last_candle["volume"] > (avg_volume * 2)

        if higher_low and consecutive_green and volume_spike:
            logger.info(
                "[%s] 반등 신호 포착: 고점 상향, 연속 양봉, 거래량 증가 조건 충족",
                code,
            )
            return True

        logger.debug(
            "[%s] 반등 신호 없음: 고점상향=%s, 연속양봉=%s, 거래량증가=%s",
            code,
            higher_low,
            consecutive_green,
            volume_spike,
        )
        return False
    except Exception as exc:  # pragma: no cover - 종목별 데이터 누락 등
        logger.error("[%s] 반등 신호 계산 중 예외: %s", code, exc, exc_info=True)
        return False


def _normalize_datetime(value) -> Optional[datetime]:
    if value is None:
        return None

    if isinstance(value, str):
        candidate = value.replace("Z", "+00:00")
        try:
            value = datetime.fromisoformat(candidate)
        except ValueError:
            return None

    if not isinstance(value, datetime):
        return None

    tz = value.tzinfo
    if tz is not None and tz.utcoffset(value) is not None:
        return value.astimezone().replace(tzinfo=None)
    return value


def on_news_event(
    news_item: Dict,
    swing_candidates: Dict,
    broker: KISAccountManager,
    position_mgr: RealPositionManager,
    cfg: Dict,
    now_fn: Callable[[], datetime] = datetime.now,
) -> None:
    published_at = _normalize_datetime(news_item.get("published_at"))
    now = _normalize_datetime(now_fn())

    if not published_at or not now:
        return

    if (now - published_at).total_seconds() > 600:
        return

    code = match_stock_symbol(news_item, swing_candidates)
    if not code:
        return

    name = swing_candidates.get(code, {}).get("name", "")
    if is_etf_like(name, code, cfg.get("trading", {})):
        return

    if position_mgr.has_position(code) or broker.has_open_order(code):
        logger.info(
            "[NEWS-HANDLER] 기존 보유/미체결 주문으로 뉴스 매수를 건너뜁니다: %s(%s)",
            name,
            code,
        )
        return

    if not news_deduper.allow(code, now):
        return

    market_cache = getattr(broker, "market_cache", None)
    if market_cache is None:
        logger.warning("[NEWS-HANDLER] MarketCache가 없어 뉴스 기반 진입을 생략합니다")
        return

    if not check_reversal_signals(code, market_cache):
        logger.debug("[%s] 뉴스 발생에도 반등 신호가 없어 매수를 보류합니다.", code)
        return

    trading_config = cfg.get("trading", {})
    buy_qty = trading_config.get("swing_buy_qty", 1)

    quote_info = market_cache.get_quote_full(code)
    if not quote_info or quote_info.get("ask_price", 0) <= 0:
        logger.warning(
            "[NEWS-BUY] %s (%s) 호가 정보를 확인하지 못해 매수를 건너뜁니다.",
            name,
            code,
        )
        return

    best_ask = quote_info.get("ask_price", 0)
    if best_ask <= 0:
        logger.warning(
            "[NEWS-BUY] %s(%s) 최우선 매도 호가가 없어 매수를 건너뜁니다.",
            name,
            code,
        )
        return

    limit_px = round(best_ask * 1.001, 2)
    logger.info(
        "[NEWS-BUY] 뉴스 반등 신호 확인, 매수 진입: %s(%s), 수량: %s, 지시가: %s",
        name,
        code,
        buy_qty,
        limit_px,
    )

    res = broker.place_buy_with_limit_then_market(
        stock_code=code,
        quantity=buy_qty,
        limit_price=limit_px,
    )

    if res.ok and res.filled_qty > 0:
        logger.info(
            "[NEWS-BUY] 매수 체결 완료: %s(%s), 체결 수량: %s, 메시지: %s",
            name,
            code,
            res.filled_qty,
            res.msg,
        )
        position_mgr.add_position(code, res.filled_qty, best_ask, name)
    else:
        logger.error(
            "[NEWS-BUY] 매수 실패: %s(%s), 메시지: %s",
            name,
            code,
            res.msg,
        )

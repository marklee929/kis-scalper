from typing import List, Dict
from core.config import config
import logging
import re
import numpy as np

logger = logging.getLogger(__name__)

def is_etf_like(name: str, code: str, trading_conf: dict) -> bool:
    """ETF/ETN과 유사한 종목인지 확인합니다."""
    if not name:
        return False
    
    name_upper = name.upper()
    
    for keyword in trading_conf.get("exclude_keywords", []):
        if keyword.upper() in name_upper:
            return True
            
    for pattern in trading_conf.get("exclude_regex", []):
        if re.search(pattern, name, re.IGNORECASE):
            return True
            
    if code and any(tag in code.upper() for tag in ["ETF", "ETN"]):
        return True
        
    return False

def _calculate_ema(prices, period):
    import pandas as pd
    return pd.Series(prices).ewm(span=period, adjust=False).mean().iloc[-1]

def _pick_swing_slice(rows: List[Dict]) -> List[Dict]:
    """조건에 따라 스윙 후보군을 선택합니다."""
    n = len(rows)
    if n < 10:
        return []  # 너무 적으면 포기
    if n < 30:
        return rows[int(n * 0.5):]  # 하위 50%로 완화
    if n < 70:
        return rows[int(n * 0.6):]  # 하위 40%
    return rows[39:70]  # 40~70위


def get_swing_candidates(volume_stocks: List[Dict], config_obj: dict, market_cache) -> List[Dict]:
    """
    거래량 상위 목록에서 스윙 트레이딩 후보를 추출합니다.
    - 거래량 순위 40~70위 구간 또는 하위 40% 종목을 대상으로 합니다.
    - ETF 등 제외 키워드/정규식이 포함된 종목을 필터링합니다.
    - 단기 하락 추세 종목을 필터링합니다. (5-EMA < 20-EMA)
    """
    cand_raw = _pick_swing_slice(volume_stocks)
    logger.info(f"[SWING] Picked {len(cand_raw)} candidates from {len(volume_stocks)} volume stocks for swing screening.")

    trading_conf = config_obj.get("trading", {})
    
    filtered_candidates = []
    etf_drop_count = 0
    trend_drop_count = 0

    for s in cand_raw:
        code = s.get("code", "")
        name = s.get("name", "")

        if is_etf_like(name, code, trading_conf):
            logger.info(f"[SWING-FILTER] drop ETF-like: {code} {name}")
            etf_drop_count += 1
            continue

        # 하락 추세 필터링
        try:
            ohlcv_5m = market_cache.get_candles(code, interval=5)
            if not ohlcv_5m or len(ohlcv_5m) < 20:
                continue
            
            close_prices = [c['close'] for c in ohlcv_5m]
            ema5 = _calculate_ema(close_prices, 5)
            ema20 = _calculate_ema(close_prices, 20)

            if ema5 < ema20:
                logger.debug(f"[SWING-FILTER] 하락 추세로 스윙 후보 제외: {name}({code}) (5-EMA < 20-EMA)")
                trend_drop_count += 1
                continue
        except Exception as e:
            logger.warning(f"[SWING-FILTER] EMA 계산 오류로 {name}({code}) 스킵: {e}")
            continue

        filtered_candidates.append(s)

    logger.info(f"[SWING-FILTER] Before filter: {len(cand_raw)}, ETF drops: {etf_drop_count}, Trend drops: {trend_drop_count}, Final candidates: {len(filtered_candidates)}")
    return filtered_candidates
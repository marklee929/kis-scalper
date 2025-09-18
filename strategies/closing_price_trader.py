"""
종가 매매 전략 (고도화 버전)
- gemini.md의 6가지 코어 보강 지표 및 신규 점수식 기반
- 수급 점수(외인/기관) 추가
- 모든 파라미터를 core.config.py에서 관리
"""
from web_socket.market_cache import MarketCache
from utils.logger import logger
from api.kis_api import KISApi
from api.kis_investor import KISInvestorAPI
from analytics.supply_score import build_supply_features, calc_supply_absorb_score
from core.config import config # 중앙 설정 객체 임포트
from typing import List, Dict, Optional, Tuple
import numpy as np
import pandas as pd
from pykrx import stock
from datetime import datetime, timedelta

# ---------- 내부 유틸 ----------
def _normalize_code(code: str) -> str:
    return code if code.startswith("A") else f"A{code}"

def _safe_float(x, default: float = 0.0) -> float:
    try: return float(x)
    except (ValueError, TypeError): return default

# ---------- 필터링 함수 ----------
def apply_all_filters(candidates: List[Dict], market_cache: MarketCache) -> List[Dict]:
    """gemini.md에 명시된 모든 필터를 순차적으로 적용하며, 각 단계에서 상세 로그를 남깁니다."""
    if not candidates:
        return []

    # 설정 파일에서 필터링 파라미터 로드
    trading_config = config.get_trading_config()
    min_turnover = trading_config.get('min_turnover', 10000000000)
    max_spread_pct = trading_config.get('max_spread_pct', 0.0015)
    exclude_keywords = trading_config.get('exclude_keywords', [])

    rejection_counts = {
        "keyword": 0,
        "turnover": 0,
        "spread": 0,
        "total_candidates": len(candidates)
    }
    final_candidates = []

    for c in candidates:
        code = c.get('code', '')
        name = c.get('name', '')
        turnover = _safe_float(c.get('turnover'))

        # 1. 키워드 필터
        if any(keyword.upper() in name.upper() for keyword in exclude_keywords):
            logger.debug(f"[FILTER] {name}({code}) 제외: 제외 키워드 포함")
            rejection_counts["keyword"] += 1
            continue

        # 2. 최소 거래대금 필터
        if turnover < min_turnover:
            logger.debug(f"[FILTER] {name}({code}) 제외: 거래대금 미달 ({turnover:,.0f} < {min_turnover:,.0f})")
            rejection_counts["turnover"] += 1
            continue

        # 3. 유동성 필터 (호가 스프레드)
        spread_pct = market_cache.get_spread_pct(code)
        if spread_pct > max_spread_pct:
            logger.debug(f"[FILTER] {name}({code}) 제외: 스프레드 과다 ({spread_pct:.4f}% > {max_spread_pct}%)")
            rejection_counts["spread"] += 1
            continue

        final_candidates.append(c)
    
    logger.info(
        f"[FILTER] 필터링 결과: "
        f"총 {rejection_counts['total_candidates']}개 중 "
        f"{len(final_candidates)}개 통과. "
        f"탈락 사유: 키워드({rejection_counts['keyword']}개), "
        f"거래대금({rejection_counts['turnover']}개), "
        f"스프레드({rejection_counts['spread']}개)"
    )
    return final_candidates

# ---------- 지표 계산 함수 (이하 동일) ----------
def _get_vwap(candles: List[Dict]) -> float:
    if not candles: return 0.0
    total_pv = sum(_safe_float(c.get('close')) * _safe_float(c.get('volume')) for c in candles)
    total_vol = sum(_safe_float(c.get('volume')) for c in candles)
    return total_pv / total_vol if total_vol > 0 else 0.0

def calculate_closing_drive(candles: List[Dict], daily_atr: float) -> float:
    if not candles or daily_atr == 0: return 50.0
    closing_candles = [c for c in candles if c['time'][8:12] >= '1500' and c['time'][8:12] <= '1520']
    if len(closing_candles) < 5: return 50.0
    prices = [_safe_float(c['close']) for c in closing_candles]
    x = np.arange(len(prices))
    try:
        slope, _ = np.polyfit(x, prices, 1)
        avg_price = np.mean(prices)
        if avg_price == 0: return 50.0
        standardized_slope = (slope / avg_price) * 10000
        cd_score = (standardized_slope / daily_atr) * 50 + 50
        return np.clip(cd_score, 0, 100)
    except (np.linalg.LinAlgError, ValueError):
        return 50.0

def calculate_vwap_premium(close_price: float, vwap: float) -> float:
    if vwap == 0: return 50.0
    premium = (close_price - vwap) / vwap * 100
    score = 50 + (premium * 25)
    return np.clip(score, 0, 100)

def calculate_last_30min_volume_pct(candles: List[Dict]) -> float:
    if not candles: return 0.0
    last_30_candles = [c for c in candles if c['time'][8:12] >= '1500']
    last_30_vol = sum(_safe_float(c.get('volume')) for c in last_30_candles)
    total_vol = sum(_safe_float(c.get('volume')) for c in candles)
    if total_vol == 0: return 0.0
    pct = (last_30_vol / total_vol) * 100
    score = 25 + (pct * 2.5)
    return np.clip(score, 0, 100)

def calculate_liquidity_penalty(market_cache: MarketCache, code: str) -> float:
    spread_pct = market_cache.get_spread_pct(code)
    penalty_score = (spread_pct - 0.1) * 250
    return np.clip(penalty_score, 0, 100)

def calculate_ma_alignment(candles: List[Dict]) -> float:
    if len(candles) < 60: return 50.0
    prices = [_safe_float(c['close']) for c in candles]
    ma5 = np.mean(prices[-5:])
    ma20 = np.mean(prices[-20:])
    ma60 = np.mean(prices[-60:])
    if not (ma5 and ma20 and ma60): return 50.0
    if ma5 > ma20 > ma60: return 100.0
    if ma5 > ma20: return 80.0
    if ma20 > ma60: return 60.0
    return 40.0

def calculate_req(code: str, candles: List[Dict]) -> float:
    if len(candles) < 2: return 50.0
    today_str = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=40)).strftime("%Y%m%d")
    try:
        df_atr = stock.get_market_ohlcv(start_date, today_str, code)
        if len(df_atr) < 20: return 50.0
        df_atr['tr'] = np.maximum(df_atr['고가'] - df_atr['저가'], 
                                 abs(df_atr['고가'] - df_atr['종가'].shift(1)), 
                                 abs(df_atr['저가'] - df_atr['종가'].shift(1)))
        atr_20d = df_atr['tr'].rolling(window=20).mean().iloc[-1]
        if atr_20d == 0: return 50.0

        high_price = max(_safe_float(c['high']) for c in candles)
        low_price = min(_safe_float(c['low']) for c in candles)
        true_range_day = high_price - low_price

        up_candles = sum(1 for c in candles if _safe_float(c['close']) > _safe_float(c['open']))
        up_candle_ratio = up_candles / len(candles) if candles else 0

        close_price = _safe_float(candles[-1]['close'])
        cr = (close_price - low_price) / (high_price - low_price + 1e-6)

        req_score = (true_range_day / atr_20d) * (up_candle_ratio**0.4) * (cr**0.3) * 50
        return np.clip(req_score, 0, 100)
    except Exception as e:
        logger.debug(f"[METRIC] REQ 계산 실패 {code}: {e}")
        return 50.0

def calculate_relative_strength(code: str, candles: List[Dict]) -> Tuple[float, float]:
    try:
        today_str = datetime.now().strftime("%Y%m%d")
        late_candles = [c for c in candles if '1450' <= c['time'][8:12] <= '1520']
        if len(late_candles) < 2: return 50.0, 50.0

        stock_start_price = _safe_float(late_candles[0]['open'])
        stock_end_price = _safe_float(late_candles[-1]['close'])
        if stock_start_price == 0: return 50.0, 50.0
        stock_return = (stock_end_price - stock_start_price) / stock_start_price * 100

        market = stock.get_market_fundamental_by_date(today_str, today_str, code).iloc[0]['시장']
        market_index_code = "1001" if market == 'KOSPI' else "2001"

        df_index = stock.get_index_ohlcv(today_str, today_str, market_index_code, 'm')
        df_index_late = df_index.between_time('14:50', '15:20')
        if len(df_index_late) < 2: return 50.0, 50.0

        index_start_price = df_index_late['시가'].iloc[0]
        index_end_price = df_index_late['종가'].iloc[-1]
        if index_start_price == 0: return 50.0, 50.0
        index_return = (index_end_price - index_start_price) / index_start_price * 100

        rs = stock_return - index_return
        rs_score = np.clip(50 + (rs * 10), 0, 100)
        return rs_score, 50.0
    except Exception as e:
        logger.debug(f"[METRIC] RS 계산 실패 {code}: {e}")
        return 50.0, 50.0

def calculate_closing_price_score(market_cache: MarketCache, api: KISApi, code: str, stock_info: Dict) -> Dict:
    """모든 지표를 계산하고 최종 점수를 반환합니다. 수급 점수를 포함합니다."""
    ncode = _normalize_code(code)
    candles = list(market_cache.get_candles(ncode, 1))
    if not candles: return {'total_score': 0.0, 'scores': {}}

    # 설정에서 가중치 로드
    weights = config.get('trading.strategy_weights', {})

    close_price = _safe_float(candles[-1]['close'])
    high_price = max(_safe_float(c['high']) for c in candles)
    low_price = min(_safe_float(c['low']) for c in candles)
    daily_atr = high_price - low_price

    # 기본 점수 계산
    cd = calculate_closing_drive(candles, daily_atr)
    vwap = market_cache.get_daily_vwap(ncode)
    pvap = calculate_vwap_premium(close_price, vwap)
    v30 = calculate_last_30min_volume_pct(candles)
    lp = calculate_liquidity_penalty(market_cache, ncode)
    ma_align = calculate_ma_alignment(candles)
    req = calculate_req(code, candles)
    rs_mkt, rs_sector = calculate_relative_strength(code, candles)

    base_score = (
        weights.get('cd', 0.20) * cd +
        weights.get('pvap', 0.15) * pvap +
        weights.get('v30', 0.20) * v30 +
        weights.get('req', 0.15) * req +
        weights.get('rs_mkt', 0.15) * rs_mkt +
        weights.get('rs_sector', 0.10) * rs_sector +
        weights.get('ma_align', 0.05) * ma_align +
        weights.get('lp', -0.10) * lp
    )
    
    # 수급 점수 계산
    supply_score = 0.0
    try:
        investor_api = KISInvestorAPI(api)
        today_str = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=10)).strftime("%Y%m%d")
        
        df_cap = stock.get_market_cap_by_date(start_date, today_str, code)
        if not df_cap.empty:
            freefloat_rate = df_cap['유통비율'].iloc[-1] if '유통비율' in df_cap.columns and not pd.isna(df_cap['유통비율'].iloc[-1]) else 30.0
            market_cap = df_cap['시가총액'].iloc[-1]
            freefloat_mktcap = market_cap * (freefloat_rate / 100)

            if freefloat_mktcap > 0:
                trends = investor_api.fetch_investor_trend_daily(code, days=5)
                features = build_supply_features(trends, freefloat_mktcap)
                
                df_ohlcv = stock.get_market_ohlcv(start_date, today_str, code)
                daily_data = {
                    'close': close_price,
                    'prev_close': _safe_float(df_ohlcv.iloc[-2]['종가']) if len(df_ohlcv) > 1 else close_price,
                    'turnover_rank': stock_info.get('rank', 999)
                }
                supply_score = calc_supply_absorb_score(features, daily_data, {})
    except Exception as e:
        logger.debug(f"[METRIC] Supply Score 계산 실패 {code}: {e}")
        supply_score = 0.0

    # 최종 점수: 기본 점수(0-100) + 수급 점수(0-50)
    supply_multiplier = weights.get('supply_score_multiplier', 0.5)
    final_score = base_score + (supply_score * supply_multiplier)

    all_scores = {
        'cd': cd, 'pvap': pvap, 'v30': v30, 'req': req, 'lp': lp, 
        'ma': ma_align, 'rs_mkt': rs_mkt, 'supply': supply_score
    }

    return {
        'code': code,
        'name': stock_info.get('name', ''),
        'turnover': stock_info.get('turnover', 0),
        'total_score': np.clip(final_score, 0, 150),
        'scores': {k: round(v, 1) for k, v in all_scores.items()}
    }

# ---------- 메인 스크리너 ----------
def closing_price_stock_filter(market_cache: MarketCache, candidates: List[Dict], api: KISApi) -> List[Dict]:
    """후보군 필터링 및 스코어링을 수행하는 메인 함수"""
    logger.info(f"종가매매 스크리너 시작. 후보: {len(candidates)}개")
    
    # 1. 필터링 적용
    filtered_candidates = apply_all_filters(candidates, market_cache)
    
    # 2. 스코어링
    scored_results = []
    for stock_info in filtered_candidates:
        try:
            code = stock_info['code']
            score_data = calculate_closing_price_score(market_cache, api, code, stock_info)
            if score_data['total_score'] > 0:
                scored_results.append(score_data)
        except Exception as e:
            logger.error(f"스코어 계산 중 오류 발생 ({stock_info.get('code')}): {e}", exc_info=False)

    # 3. 점수 및 거래대금으로 정렬하여 상위 30개 반환
    scored_results.sort(key=lambda x: (x['total_score'], x['turnover']), reverse=True)
    
    top_30 = scored_results[:30]
    logger.info(f"최종 후보 선정: {len(top_30)}개")
    
    return top_30
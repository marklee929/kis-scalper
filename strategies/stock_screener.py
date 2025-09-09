# filepath: c:\WORK\kis-scalper\strategies\stock_screener.py
from web_socket.market_cache import MarketCache
from utils.logger import logger
from api.kis_api import KISApi
from typing import List, Dict, Optional
import numpy as np

# ---------- 내부 유틸 ----------
def _normalize_code(code: str) -> str:
    code = (code or "").strip()
    return code if code.startswith("A") else f"A{code}"

def _safe_float(x, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default

def _estimate_turnover_from_candles(market_cache: MarketCache, ncode: str, fallback_price: float) -> float:
    """분 단위 캔들에서 거래대금(원) 근사치 산출: sum(volume_i * close_i)"""
    try:
        candles = market_cache.get_candles(ncode, 1)  # 1분봉
        if not candles:
            return 0.0
        tot = 0.0
        for c in candles:
            v = _safe_float(c.get("volume") or c.get("vol"), 0.0)
            px = _safe_float(c.get("close"), 0.0) or fallback_price
            if v > 0 and px > 0:
                tot += v * px
        return tot
    except Exception:
        return 0.0

# ---------- 메인 스크리너 ----------
def scalping_stock_filter(market_cache: MarketCache, candidates: List[Dict], api: KISApi) -> List[Dict]:
    """
    단타에 적합한 종목 필터링
    전략:
      1) ETF 등 제외
      2) 모든 후보 점수화 (절대점수 컷 없음)
      3) 최소 안전조건(기본) 통과 대상에서 점수 상위 N개 선출
         - 최소 안전조건 실패 시에도 완전 빈 리스트 방지 위해 상위 N개 보정
    """
    EXCLUDE_KEYWORDS = ["KODEX", "TIGER", "ARIRANG", "HANARO", "KBSTAR", "KOSEF"]
    PASS_TOP_N = 30

    pre_filtered_candidates = []
    for stock in candidates:
        stock_name = stock.get('name', '') or stock.get('hts_kor_isnm', '')
        if any(keyword in stock_name for keyword in EXCLUDE_KEYWORDS):
            logger.debug(f"[SCREENER] ETF 제외: {stock_name}")
            continue
        pre_filtered_candidates.append(stock)

    logger.info(f"[SCREENER] 종목 스크리닝 시작: {len(pre_filtered_candidates)}개 후보 (ETF 제외 후)")

    scored = []
    for stock in pre_filtered_candidates:
        try:
            code = stock.get('code', stock.get('symbol', ''))
            if not code:
                continue
            score_data = calculate_scalping_score(market_cache, code, api, stock)
            stock.update(score_data)
            scored.append(stock)
        except Exception as e:
            logger.debug(f"[SCREENER] 종목 분석 실패 {stock.get('code', stock.get('symbol',''))}: {e}")
            continue

    if not scored:
        logger.warning("[SCREENER] 점수화 결과가 비었습니다. 입력 후보/캐시/심볼 포맷 확인 필요.")
        return []

    # 최소 안전조건: 유동성/거래대금/모멘텀 하한
    eligible = [
        s for s in scored
        if s.get('individual_scores', {}).get('liquidity', 0) >= 40
        and s.get('individual_scores', {}).get('turnover', 0)  >= 60
        and s.get('individual_scores', {}).get('momentum', 0)   >= 40
    ]

    # 조건 통과가 너무 적으면, 일단 전체에서 상위 N개를 뽑아 관찰 가능하게 유지
    pool = eligible if len(eligible) >= 5 else scored

    pool.sort(key=lambda x: x.get('total_score', 0.0), reverse=True)
    top_stocks = pool[:PASS_TOP_N]

    avg = sum(s.get('total_score', 0.0) for s in top_stocks) / max(len(top_stocks), 1)
    logger.info(f"[SCREENER] 선별 완료: {len(top_stocks)}개 (평균점수: {avg:.1f}) / 후보총 {len(scored)}개")

    # 디버그: 상위 5개 이유 로그
    for s in top_stocks[:5]:
        ind = s.get('individual_scores', {})
        logger.debug(
            f"[SCREENER][TOP] {s.get('name','')}/{s.get('code','')} "
            f"score={s.get('total_score'):.1f} LQ={ind.get('liquidity',0)} "
            f"VOL={ind.get('volatility',0)} SPR={ind.get('spread',0)} "
            f"TO={ind.get('turnover',0)} MOM={ind.get('momentum',0)}"
        )

    return top_stocks

def calculate_scalping_score(market_cache: MarketCache, code: str, api: KISApi, stock_info: Dict) -> Dict:
    """
    단타 적합도 점수 계산 (가중합=100 기준)
    - 유동성 25, 변동성 20, 스프레드 10, 거래대금 20, 모멘텀 25
    """
    scores: Dict[str, float] = {}
    weights = {
        'liquidity': 25,
        'volatility': 20,
        'spread':     10,
        'turnover':   20,  # 기존 10 -> 20으로 상향, 합계=100
        'momentum':   25,
    }

    try:
        raw_code = code
        ncode = _normalize_code(code)

        # 가격
        current_price = stock_info.get('current_price')
        if not current_price:
            current_price = get_current_price(market_cache, raw_code, api, ncode)

        current_price = _safe_float(current_price, 0.0)

        # 거래대금(누적) 확보: 후보 딕셔너리에 없으면 캔들로 근사
        volume_turnover = _safe_float(stock_info.get('volume_turnover'), 0.0)
        if volume_turnover <= 0.0:
            vt_est = _estimate_turnover_from_candles(market_cache, ncode, current_price)
            if vt_est > 0:
                volume_turnover = vt_est

        # 1) 유동성(누적 거래대금) 점수
        #   100억/500억/1000억+ 구간. (원 단위)
        if volume_turnover > 1000e8:      # 1000억 이상
            scores['liquidity'] = 100
        elif volume_turnover > 500e8:     # 500억 이상
            scores['liquidity'] = 80
        elif volume_turnover > 100e8:     # 100억 이상
            scores['liquidity'] = 60
        elif volume_turnover > 30e8:      # 30억 이상
            scores['liquidity'] = 40
        else:
            scores['liquidity'] = 20

        # 2) 1분 변동성 점수 (현실화)
        daily_volatility = calculate_daily_volatility(market_cache, ncode)
        # daily_volatility = 1분 수익률 표준편차(%) 가정
        # 일반적으로 0.05%~0.7% 구간이 실전 단타 '적당한' 변동성
        dv = daily_volatility
        if 0.15 <= dv <= 0.70:
            scores['volatility'] = 100
        elif 0.10 <= dv < 0.15 or 0.70 < dv <= 1.00:
            scores['volatility'] = 80
        elif 0.05 <= dv < 0.10 or 1.00 < dv <= 1.50:
            scores['volatility'] = 60
        else:
            scores['volatility'] = 40  # 너무 낮아도/높아도 페널티

        # 3) 호가 스프레드 점수
        spread = estimate_spread(current_price)
        if spread <= 0.20:
            scores['spread'] = 100
        elif spread <= 0.30:
            scores['spread'] = 80
        elif spread <= 0.50:
            scores['spread'] = 60
        else:
            scores['spread'] = 40

        # 4) 거래대금 점수 (시장 관심도)
        if volume_turnover > 1000e8:
            scores['turnover'] = 100
        elif volume_turnover > 500e8:
            scores['turnover'] = 80
        elif volume_turnover > 100e8:
            scores['turnover'] = 60
        else:
            scores['turnover'] = 40

        # 5) 단기 모멘텀 점수 (5분)
        momentum_5m = get_momentum(market_cache, ncode, minutes=5)
        if momentum_5m > 1.0:
            scores['momentum'] = 100
        elif momentum_5m > 0.5:
            scores['momentum'] = 80
        elif momentum_5m > 0.0:
            scores['momentum'] = 60
        elif momentum_5m > -0.3:  # -0.5 -> -0.3로 완화 (상승 전 눌림 허용)
            scores['momentum'] = 40
        else:
            scores['momentum'] = 20

        # 가중합(합계=100)
        total_score = sum((scores[k] * weights[k]) / 100.0 for k in weights.keys())

        return {
            'total_score': float(total_score),
            'individual_scores': scores,
            'current_price': current_price,
            'daily_volatility': float(dv),
            'volume_turnover': float(volume_turnover),
            'momentum_5m': float(momentum_5m),
            'spread_pct': float(spread),
        }

    except Exception as e:
        logger.error(f"[SCREENER] 점수 계산 실패 {code}: {e}")
        return {'total_score': 0.0, 'individual_scores': {}}

def get_current_price(market_cache: MarketCache, raw_code: str, api: KISApi, ncode: Optional[str]=None) -> float:
    """현재가 조회: 캐시(정규코드) -> API(원코드 순)"""
    try:
        n = ncode or _normalize_code(raw_code)
        quote = market_cache.get_quote_full(n)
        if quote and 'price' in quote and _safe_float(quote['price']) > 0:
            return float(quote['price'])

        # API는 종종 A 프리픽스 없이 받음
        code_for_api = raw_code.lstrip("A")
        response = api.get_current_price(code_for_api)
        if response and 'output' in response:
            return _safe_float(response['output'].get('stck_prpr'), 0.0)
        return 0.0
    except Exception as e:
        logger.debug(f"[SCREENER] 현재가 조회 실패 {raw_code}: {e}")
        return 0.0

def calculate_daily_volatility(market_cache: MarketCache, ncode: str) -> float:
    """1분봉 기반 변동성(최근 20분) 표준편차(%). 데이터 부족 시 보수적 기본값."""
    try:
        candles = market_cache.get_candles(ncode, 1)  # 1분봉
        if len(candles) < 10:
            return 0.30  # 기본값 현실화 (0.30%)

        prices = [c.get('close') for c in candles if _safe_float(c.get('close'), 0.0) > 0]
        if len(prices) < 10:
            return 0.30

        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                ret = (prices[i] - prices[i-1]) / prices[i-1] * 100.0
                returns.append(ret)

        if not returns:
            return 0.30
        return float(np.std(returns))
    except Exception:
        return 0.30

def estimate_spread(price: float) -> float:
    """호가 스프레드 추정(%). KIS 호가단위 기준."""
    p = _safe_float(price, 0.0)
    if p <= 0:
        return 100.0
    try:
        if p < 2000:
            tick = 1
        elif p < 5000:
            tick = 5
        elif p < 20000:
            tick = 10
        elif p < 50000:
            tick = 50
        elif p < 200000:
            tick = 100
        else:
            tick = 500
        return (tick / p) * 100.0
    except Exception:
        return 1.0

def get_momentum(market_cache: MarketCache, ncode: str, minutes: int = 5) -> float:
    """단기 모멘텀 계산 (N분간 종가 대비 수익률, %)"""
    try:
        candles = market_cache.get_candles(ncode, 1)
        if len(candles) < minutes + 1:
            return 0.0
        a = _safe_float(candles[-minutes-1].get('close'), 0.0)
        b = _safe_float(candles[-1].get('close'), 0.0)
        if a <= 0 or b <= 0:
            return 0.0
        return (b - a) / a * 100.0
    except Exception:
        return 0.0

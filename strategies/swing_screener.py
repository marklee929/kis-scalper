from typing import List, Dict, Optional
from core.config import config
import logging
import json
from datetime import datetime

# 로깅 설정
logger = logging.getLogger(__name__)

# 제외 키워드 (ETF, ETN, 우선주 등)
EXCLUDE_KEYWORDS = config.get('trading', {}).get('exclude_keywords', [])

def get_swing_candidates(
    market_cache, 
    all_stocks: List[Dict], 
    api
) -> List[Dict]:
    """
    실시간 데이터를 기반으로 스윙 트레이딩 후보를 선정합니다.
    gemini.md 문서의 개선안을 따릅니다.

    Args:
        market_cache: 실시간 시세 및 체결 데이터를 관리하는 객체.
        all_stocks (List[Dict]): 전체 종목 리스트.
        api: KIS API 핸들러.

    Returns:
        List[Dict]: 필터링 및 점수화된 스윙 후보 종목 리스트.
    """
    swing_candidates = []
    
    for stock in all_stocks:
        code = stock.get("code")
        name = stock.get("name", "")

        # 1. 기본 필터링
        # ETF/ETN/우선주/잡주 제외
        if any(keyword.upper() in name.upper() for keyword in EXCLUDE_KEYWORDS):
            continue

        # 실시간 데이터 조회
        current_data = market_cache.get_current_data(code)
        if not current_data:
            continue

        # 거래대금 10억 이상 필터
        if current_data.get('acc_trading_value', 0) < 1_000_000_000:
            continue

        # 2. 점수화
        score = 0
        details = {}

        # 2.1. 거래량 변화율 (ΔVolume) 점수 (최대 50점)
        vol_ratio = calculate_volume_ratio(code, market_cache)
        if vol_ratio >= 3:
            score += min(50, (vol_ratio - 3) * 10)
        details['volume_ratio'] = vol_ratio

        # 2.2. 체결강도 점수 (최대 30점)
        strength = current_data.get('strength', 0)
        if strength >= 120:
            score += min(30, (strength - 120) / 10 * 3)
        details['strength'] = strength
        
        # 2.3. 가격 추세 점수 (최대 20점)
        price_trend = calculate_price_trend(code, market_cache)
        if price_trend >= 1.0:
            score += min(20, (price_trend - 1.0) * 10)
        details['price_trend'] = price_trend

        # 3. 추가 필터
        # 호가 비율 확인
        orderbook = market_cache.get_orderbook(code)
        if orderbook:
            bid_qty = sum(orderbook.get('bid_hoga', {}).values())
            ask_qty = sum(orderbook.get('ask_hoga', {}).values())
            if ask_qty > 0 and (bid_qty / ask_qty) < 1.2:
                continue
        
        # 고점 대비 괴리율 확인
        high_price = current_data.get('high', 0)
        current_price = current_data.get('price', 0)
        if high_price > 0 and ((high_price - current_price) / high_price) * 100 > 2.0:
            continue

        # 4. 최종 후보 선정
        if score >= 70:
            stock_info = {
                "code": code,
                "name": name,
                "score": score,
                "details": details,
                "timestamp": datetime.now().isoformat()
            }
            swing_candidates.append(stock_info)

    # 점수 순으로 정렬
    sorted_candidates = sorted(swing_candidates, key=lambda x: x['score'], reverse=True)
    
    # 결과 저장
    if sorted_candidates:
        log_filename = f"logs/swing_candidates_{datetime.now().strftime('%Y-%m-%d')}.json"
        with open(log_filename, 'a', encoding='utf-8') as f:
            for candidate in sorted_candidates:
                f.write(json.dumps(candidate, ensure_ascii=False) + '\n')

    return sorted_candidates[:10] # 상위 10개 종목만 반환


def calculate_volume_ratio(code: str, market_cache) -> float:
    """최근 1분 거래량 / 직전 5분 평균 거래량 계산"""
    try:
        # `get_trading_volume`은 분단위 거래량 리스트를 반환한다고 가정
        # 예: [현재-1분, 현재-2분, ..., 현재-6분]
        volumes = market_cache.get_trading_volume(code, interval='1min', periods=6)
        if not volumes or len(volumes) < 6:
            return 0.0
        
        recent_volume = volumes[0]
        prev_5min_avg = sum(volumes[1:]) / 5
        
        if prev_5min_avg == 0:
            return float('inf') if recent_volume > 0 else 0.0
            
        return recent_volume / prev_5min_avg
    except Exception as e:
        logger.error(f"[{code}] 거래량 비율 계산 오류: {e}")
        return 0.0

def calculate_price_trend(code: str, market_cache) -> float:
    """현재가 / 직전 5분 저가 계산"""
    try:
        # `get_ohlcv`는 분단위 OHLCV 리스트를 반환한다고 가정
        ohlcv = market_cache.get_ohlcv(code, interval='1min', periods=5)
        if not ohlcv or len(ohlcv) < 5:
            return 0.0
            
        prev_5min_low = min(item['low'] for item in ohlcv)
        current_price = market_cache.get_current_data(code).get('price', 0)

        if prev_5min_low == 0:
            return 0.0
            
        return (current_price / prev_5min_low - 1) * 100
    except Exception as e:
        logger.error(f"[{code}] 가격 추세 계산 오류: {e}")
        return 0.0
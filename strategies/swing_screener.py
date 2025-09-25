from typing import List, Dict
from core.config import config

def get_swing_candidates(volume_stocks: List[Dict]) -> List[Dict]:
    """
    거래량 상위 목록에서 스윙 트레이딩 후보를 추출합니다.
    - 거래량 순위 40~70위 구간 또는 하위 40% 종목을 대상으로 합니다.
    - 설정에 따라 ETF 등 제외 키워드가 포함된 종목을 필터링합니다.

    Args:
        volume_stocks (List[Dict]): 거래량 순위 상위 종목 리스트.
                                    각 항목은 'name', 'code' 등을 포함해야 합니다.
    Returns:
        List[Dict]: 필터링된 스윙 후보 종목 리스트.
    """
    
    # 1. 스윙 후보 원본 추출 (동적 구간 설정)
    num_volume_stocks = len(volume_stocks)
    swing_candidates_raw = []
    if num_volume_stocks >= 70:
        swing_candidates_raw = volume_stocks[39:70]  # 40위 ~ 70위
    elif num_volume_stocks >= 30:
        # 목록이 30개 이상 70개 미만일 경우 하위 40%를 선택
        start_index = int(num_volume_stocks * 0.6)
        swing_candidates_raw = volume_stocks[start_index:]

    if not swing_candidates_raw:
        return []

    # 2. 스윙 후보에서 ETF 등 제외
    trading_config = config.get('trading', {})
    exclude_keywords = trading_config.get('exclude_keywords', [])
    
    filtered_swing_candidates = []
    for stock in swing_candidates_raw:
        stock_name = stock.get('name', '')
        if not any(keyword.upper() in stock_name.upper() for keyword in exclude_keywords):
            filtered_swing_candidates.append(stock)
            
    return filtered_swing_candidates

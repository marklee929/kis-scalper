from typing import List, Dict
from core.config import config
import logging
import re

logger = logging.getLogger(__name__)

def is_etf_like(name: str, code: str, trading_conf: dict) -> bool:
    """ETF/ETN과 유사한 종목인지 확인합니다."""
    if not name:
        return False
    
    name_upper = name.upper()
    
    # 1) 키워드 매칭
    for keyword in trading_conf.get("exclude_keywords", []):
        if keyword.upper() in name_upper:
            return True
            
    # 2) 정규식 매칭
    for pattern in trading_conf.get("exclude_regex", []):
        if re.search(pattern, name, re.IGNORECASE):
            return True
            
    # 3) 종목 코드 패턴 (안전장치)
    if code and any(tag in code.upper() for tag in ["ETF", "ETN"]):
        return True
        
    return False

def get_swing_candidates(volume_stocks: List[Dict], config_obj: dict) -> List[Dict]:
    """
    거래량 상위 목록에서 스윙 트레이딩 후보를 추출합니다.
    - 거래량 순위 40~70위 구간 또는 하위 40% 종목을 대상으로 합니다.
    - ETF 등 제외 키워드/정규식이 포함된 종목을 필터링합니다.
    """
    n = len(volume_stocks)
    if n < 30:
        return []

    if n >= 70:
        cand_raw = volume_stocks[39:70]      # 40~70위
    else:
        start = max(0, int(n * 0.6))         # 30~69개면 하위 40%
        cand_raw = volume_stocks[start:]

    trading_conf = config_obj.get("trading", {})
    filtered = [
        s for s in cand_raw
        if not is_etf_like(s.get("name",""), s.get("code",""), trading_conf)
    ]
    return filtered
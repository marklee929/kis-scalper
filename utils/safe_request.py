import time
from requests import Session, RequestException, ConnectionError, Timeout

# 전역 세션
_session = Session()

RATE_LIMIT_DELAY = 1.2
MAX_RETRIES = 3

def safe_request(method, url, **kwargs):
    """
    method: _session.get 혹은 _session.post
    url: 호출 URL
    kwargs: headers, params, json, timeout 등
    """
    kwargs.setdefault("timeout", 10)

    from utils.logger import logger
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            res = method(url, **kwargs)
            res.raise_for_status()
            data = res.json()
            time.sleep(RATE_LIMIT_DELAY)
            return data
        except (ConnectionError, Timeout, RequestException) as e:
            logger.warning(f"[API] {method.__name__} 시도 {attempt} 실패: {e}")
            if attempt == MAX_RETRIES:
                logger.error(f"[API] {method.__name__} 최대 재시도 실패 → None 반환")
                return None
            # 지수 백오프
            time.sleep(RATE_LIMIT_DELAY * attempt)

import requests
import html
from typing import Dict, Optional
from datetime import datetime
from urllib.parse import quote

from core.config import config
from utils.logger import logger

class NaverNewsFetcher:
    """네이버 뉴스 검색 API를 다루는 클라이언트"""
    
    API_URL = "https://openapi.naver.com/v1/search/news.json"

    def __init__(self, client_id: str, client_secret: str):
        if not client_id or not client_secret:
            raise ValueError("Naver API Client ID와 Secret이 필요합니다.")
        self.headers = {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret,
        }

    def search_latest_news(self, query: str, display: int = 1) -> Optional[Dict]:
        """주어진 쿼리로 최신 뉴스를 검색하여 1건 반환합니다."""
        params = {
            "query": query,
            "display": display,
            "sort": "date" # 최신순 정렬
        }
        try:
            response = requests.get(self.API_URL, headers=self.headers, params=params, timeout=5)
            response.raise_for_status() # 200 OK가 아니면 예외 발생
            
            data = response.json()
            items = data.get("items")
            
            if not items:
                return None

            latest_item = items[0]
            
            # 날짜 형식 변환 (RFC 1123 -> HH:MM)
            pub_date = datetime.strptime(latest_item['pubDate'], '%a, %d %b %Y %H:%M:%S %z')
            formatted_time = pub_date.strftime("%H:%M")

            return {
                "title": html.unescape(latest_item['title'].replace("<b>", "").replace("</b>", "")),
                "link": latest_item['link'],
                "timestamp": formatted_time
            }

        except requests.exceptions.RequestException as e:
            logger.warning(f"[NaverNews] API 요청 실패: {e}")
            return None
        except (KeyError, IndexError, ValueError) as e:
            logger.warning(f"[NaverNews] 뉴스 데이터 파싱 실패: {e}")
            return None

# --- 전역 인스턴스 생성 ---
def create_news_fetcher() -> Optional[NaverNewsFetcher]:
    """설정에서 API 키를 읽어 인스턴스를 생성합니다."""
    try:
        naver_config = config.get('naver', {})
        client_id = naver_config.get('client_id')
        client_secret = naver_config.get('client_secret')
        if client_id and client_secret:
            return NaverNewsFetcher(client_id, client_secret)
        else:
            logger.info("[NaverNews] Naver API 설정이 없어 뉴스 기능을 비활성화합니다.")
            return None
    except Exception as e:
        logger.error(f"[NaverNews] Fetcher 생성 실패: {e}")
        return None

news_fetcher = create_news_fetcher()

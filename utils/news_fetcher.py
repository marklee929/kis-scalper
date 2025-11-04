"""
네이버 뉴스 검색 API 래퍼.
짧은 주기의 반복 호출로 429가 발생하지 않도록
쿼리별 최소 간격과 글로벌 백오프를 적용한다.
"""

from __future__ import annotations

import html
import requests
from typing import Dict, Optional
from datetime import datetime
from time import time

from core.config import config
from utils.logger import logger


class NaverNewsFetcher:
    API_URL = "https://openapi.naver.com/v1/search/news.json"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        min_interval: int = 90,
        block_seconds: int = 300,
    ) -> None:
        if not client_id or not client_secret:
            raise ValueError("Naver API Client ID와 Secret이 필요합니다.")

        self.headers = {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret,
        }
        self._min_interval = max(1, min_interval)
        self._block_seconds = max(30, block_seconds)
        self._last_query_ts: Dict[str, float] = {}
        self._block_until: float = 0.0

    def search_latest_news(self, query: str, display: int = 1) -> Optional[Dict]:
        """최신 뉴스를 조회한다. 호출 간 최소 간격과 429 백오프를 적용한다."""
        now_ts = time()
        if now_ts < self._block_until:
            return None

        normalized_query = (query or "").strip()
        if not normalized_query:
            return None

        last_ts = self._last_query_ts.get(normalized_query)
        if last_ts and (now_ts - last_ts) < self._min_interval:
            return None

        params = {
            "query": normalized_query,
            "display": display,
            "sort": "date",
        }
        self._last_query_ts[normalized_query] = now_ts

        try:
            response = requests.get(self.API_URL, headers=self.headers, params=params, timeout=5)
            if response.status_code == 429:
                self._block_until = time() + self._block_seconds
                logger.warning(
                    "[NaverNews] 429 Too Many Requests -> %d초 동안 뉴스 조회를 중단합니다",
                    self._block_seconds,
                )
                return None

            response.raise_for_status()

            data = response.json()
            items = data.get("items")
            if not items:
                return None

            latest_item = items[0]
            pub_date = datetime.strptime(latest_item["pubDate"], "%a, %d %b %Y %H:%M:%S %z")
            formatted_time = pub_date.strftime("%m-%d %H:%M")

            return {
                "title": html.unescape(latest_item["title"].replace("<b>", "").replace("</b>", "")),
                "link": latest_item["link"],
                "timestamp": formatted_time,
                "published_at": pub_date,
            }

        except requests.exceptions.RequestException as exc:
            logger.warning(f"[NaverNews] API 요청 실패: {exc}")
            return None
        except (KeyError, IndexError, ValueError) as exc:
            logger.warning(f"[NaverNews] 응답 파싱 실패: {exc}")
            return None


def create_news_fetcher() -> Optional[NaverNewsFetcher]:
    """환경설정에서 인증 정보를 읽어 fetcher를 구성한다."""
    try:
        naver_config = config.get("naver", {})
        client_id = naver_config.get("client_id")
        client_secret = naver_config.get("client_secret")
        if not (client_id and client_secret):
            logger.info("[NaverNews] Naver API 설정이 없어 뉴스 기능을 비활성화합니다.")
            return None

        news_cfg = config.get("news", {})
        min_interval = int(news_cfg.get("naver_min_interval_sec", 90))
        block_seconds = int(news_cfg.get("naver_block_seconds", 300))
        return NaverNewsFetcher(
            client_id=client_id,
            client_secret=client_secret,
            min_interval=min_interval,
            block_seconds=block_seconds,
        )
    except Exception as exc:
        logger.error(f"[NaverNews] Fetcher 생성 실패: {exc}")
        return None


news_fetcher = create_news_fetcher()

import argparse
import sys
from pathlib import Path
import json

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 프로젝트 모듈 임포트
# 순서 중요: config가 먼저 로드되어야 news_fetcher가 초기화될 수 있음
from core.config import config
from utils.news_fetcher import news_fetcher
from utils.logger import logger

def test_news_search(query: str):
    """뉴스 검색을 테스트하고 결과를 출력하는 함수"""
    print(f"\n🔍 '{query}'에 대한 최신 뉴스를 검색합니다...")
    print("="*50)

    if not news_fetcher:
        logger.error("[TEST] NaverNewsFetcher가 초기화되지 않았습니다. config/secrets.json에 NAVER_CLIENT_ID와 NAVER_CLIENT_SECRET을 확인하세요.")
        return

    latest_news = news_fetcher.search_latest_news(query)

    if latest_news:
        print("✅ 최신 뉴스 발견:")
        # 보기 좋게 JSON 형식으로 출력
        print(json.dumps(latest_news, indent=2, ensure_ascii=False))
    else:
        print("❌ 해당 검색어에 대한 최신 뉴스를 찾을 수 없습니다.")
    
    print("="*50)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="네이버 뉴스 검색 API 테스트 스크립트")
    parser.add_argument("query", type=str, help="검색할 종목명 또는 키워드")
    args = parser.parse_args()

    test_news_search(args.query)

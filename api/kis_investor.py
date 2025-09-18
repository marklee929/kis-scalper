
import requests
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class KISInvestorAPI:
    """
    KIS API를 사용하여 투자자별 매매 동향 데이터를 조회하는 클래스.
    """
    def __init__(self, api_client):
        self.api = api_client

    def fetch_investor_trend_daily(self, code: str, days: int = 5) -> List[Dict]:
        """
        지정된 기간 동안의 일별 투자자 매매 동향을 조회합니다.
        KIS API의 '종목별 투자자매매동향(일별)' (inquire-investor)를 사용합니다.
        """
        try:
            # API 엔드포인트 및 헤더 설정
            endpoint = "/uapi/domestic-stock/v1/trading-trends/inquire-investor"
            
            # 날짜 설정 (오늘부터 days일 전까지)
            today = datetime.now()
            start_date = today - timedelta(days=days*2) # 주말 포함 넉넉하게
            
            params = {
                "FID_COND_MRKT_DIV_CODE": "J", # 주식
                "FID_INPUT_ISCD": code.replace("A", ""),
                "FID_INPUT_DATE_1": start_date.strftime('%Y%m%d'),
                "FID_INPUT_DATE_2": today.strftime('%Y%m%d'),
                "FID_PERIOD_DIV_CODE": "D" # 일별
            }

            # API 호출
            response = self.api._fetch_data(endpoint, params=params)
            
            if response and response.get('rt_cd') == '0':
                trend_data = response.get('output', [])
                
                # 필요한 데이터만 추출 및 가공
                processed_data = []
                for item in trend_data[:days]: # 최근 days일 데이터만 사용
                    processed_data.append({
                        "date": item.get('stck_bsop_date'),
                        "foreign_amt": float(item.get('frgn_ntby_tr_pbmn', 0)), # 외국인 순매수 대금
                        "inst_amt": float(item.get('orgn_ntby_tr_pbmn', 0)),    # 기관 순매수 대금
                        "indiv_amt": float(item.get('prsn_ntby_tr_pbmn', 0))    # 개인 순매수 대금
                    })
                
                logger.debug(f"[{code}] 투자자 동향 조회 성공 ({len(processed_data)}일)")
                return processed_data
            else:
                logger.warning(f"[{code}] 투자자 동향 조회 실패: {response.get('msg1', 'Unknown error') if response else 'No response'}")
                return []

        except Exception as e:
            logger.error(f"[{code}] 투자자 동향 조회 중 예외 발생: {e}", exc_info=True)
            return []

# 사용 예시를 위한 스텁
if __name__ == '__main__':
    # 실제 API 클라이언트 대신 목(Mock) 객체를 사용한 테스트
    class MockApiClient:
        def _fetch_data(self, endpoint, params):
            print(f"Fetching {endpoint} with params {params}")
            # 실제 API 응답과 유사한 샘플 데이터 반환
            return {
                "rt_cd": "0",
                "msg1": "성공",
                "output": [
                    {"stck_bsop_date": "20250918", "frgn_ntby_tr_pbmn": "-10000000", "orgn_ntby_tr_pbmn": "8000000", "prsn_ntby_tr_pbmn": "2000000"},
                    {"stck_bsop_date": "20250917", "frgn_ntby_tr_pbmn": "-5000000", "orgn_ntby_tr_pbmn": "6000000", "prsn_ntby_tr_pbmn": "-1000000"},
                    {"stck_bsop_date": "20250916", "frgn_ntby_tr_pbmn": "2000000", "orgn_ntby_tr_pbmn": "-1000000", "prsn_ntby_tr_pbmn": "-1000000"},
                    {"stck_bsop_date": "20250915", "frgn_ntby_tr_pbmn": "3000000", "orgn_ntby_tr_pbmn": "-2000000", "prsn_ntby_tr_pbmn": "-1000000"},
                    {"stck_bsop_date": "20250912", "frgn_ntby_tr_pbmn": "-8000000", "orgn_ntby_tr_pbmn": "7000000", "prsn_ntby_tr_pbmn": "1000000"},
                ]
            }

    mock_api_client = MockApiClient()
    investor_api = KISInvestorAPI(api_client=mock_api_client)
    trends = investor_api.fetch_investor_trend_daily(code="005930", days=5)
    print("조회된 투자자 동향:", trends)

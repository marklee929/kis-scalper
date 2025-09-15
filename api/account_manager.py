"""
KIS API 계정 관리자 (v2: KISApi 사용 리팩토링)
"""
from typing import Dict, List
import logging
from api.kis_api import KISApi

logger = logging.getLogger(__name__)

class KISAccountManager:
    """KIS 계정 관리자 - KISApi를 사용하여 API 호출을 위임"""
    
    def __init__(self, app_key: str, app_secret: str, account_no: str):
        self.account_no = account_no
        self.api = KISApi(app_key, app_secret, account_no)
        logger.info("✅ [Manager] KISAccountManager 초기화 완료 (KISApi 사용)")

    def _get_account_parts(self):
        """계좌번호를 CANO와 ACNT_PRDT_CD로 분리"""
        account_parts = self.account_no.replace('-', '')
        return account_parts[:8], account_parts[8:]

    def get_simple_balance(self) -> int:
        """간단한 잔고 조회 - 현재 사용가능 금액만 반환"""
        try:
            cano, acnt_prdt_cd = self._get_account_parts()
            params = {
                "CANO": cano,
                "ACNT_PRDT_CD": acnt_prdt_cd,
                "PDNO": "",  # 특정 종목이 아닌 전체 계좌의 주문 가능 금액을 조회
                "ORD_DVSN": "01", # 01: 시장가
                "ORD_UNPR": "0",  # 시장가 주문 시 가격은 0
                "ORD_QTY": "0",   # 필수 파라미터. 전체 조회 시 0으로 설정.
                "CMA_EVLU_AMT_ICLD_YN": "N",
                "OVRS_ICLD_YN": "N"
            }
            data = self.api.request("get_balance", params=params)
            if data and data.get("rt_cd") == "0":
                output_data = data.get("output", {})
                # '미수없는매수가능금액'을 사용. '주문가능현금'은 D+2 예수금을 포함하지 않을 수 있음.
                available_cash = int(output_data.get("nrcvb_buy_amt", 0))
                msg = data.get('msg1', 'OK') # 응답 메시지 추출
                # logger.info(f"✅ [BALANCE] 잔고 조회 성공: {available_cash:,.0f}원 (응답: {msg})")
                return available_cash
            else:
                # 실패 시 응답 내용 로깅 강화
                # logger.warning(f"❌ [BALANCE] 잔고 조회 응답 실패. 응답: {data}")
                return 0
        except Exception as e:
            # logger.error(f"❌ [BALANCE] 간단 잔고 조회 중 예외 발생: {e}", exc_info=True)
            return 0

    def get_current_positions(self) -> List[Dict]:
        """현재 보유 종목 조회 (v2: 필수 파라미터 추가)"""
        try:
            cano, acnt_prdt_cd = self._get_account_parts()
            params = {
                "CANO": cano,
                "ACNT_PRDT_CD": acnt_prdt_cd,
                "AFHR_FLPR_YN": "N",
                "OFL_YN": "",
                "INQR_DVSN": "02",
                "UNPR_DVSN": "01",
                "FUND_STTL_ICLD_YN": "N",
                "FNCG_AMT_AUTO_RDPT_YN": "N",
                "PRCS_DVSN": "01",
                "CTX_AREA_FK100": "",
                "CTX_AREA_NK100": ""
            }
            data = self.api.request("get_holdings", params=params)
            if data and data.get("rt_cd") == "0":
                return [pos for pos in data.get("output1", []) if int(pos.get("hldg_qty", 0)) > 0]
            return []
        except Exception as e:
            logger.error(f"❌ [POSITIONS] 포지션 조회 오류: {e}")
            return []

    def _place_order(self, tr_id: str, stock_code: str, quantity: int, price: int, order_type: str) -> Dict:
        """공통 주문 함수"""
        try:
            cano, acnt_prdt_cd = self._get_account_parts()
            body = {
                "CANO": cano,
                "ACNT_PRDT_CD": acnt_prdt_cd,
                "PDNO": stock_code.lstrip('A').zfill(6),
                "ORD_DVSN": order_type, # 00: 지정가, 01: 시장가
                "ORD_QTY": str(int(quantity)),
                "ORD_UNPR": str(int(price)) # float -> int -> str 변환으로 소수점 제거
            }
            headers = {"tr_id": tr_id}

            data = self.api.request("order_cash", body=body, headers=headers)
            
            success = data and data.get("rt_cd") == "0"
            return {
                "success": success,
                "error": (data.get("msg1") if (data and not success) else ""),
                "order_no": (data.get("output", {}).get("ODNO", "") if data else ""),
                "full_response": (data or {})
            }
        except Exception as e:
            logger.error(f"❌ [ORDER] 주문 실행 오류: {e}")
            return {"success": False, "error": str(e)}

    def place_buy_order(self, stock_code: str, quantity: int, price: int) -> Dict:
        # NOTE: 현재 미사용 (향후 지정가 주문 필요시 사용)
        logger.info(f"📈 [BUY] 지정가 매수 주문: {stock_code} {quantity}주 @{price:,}원")
        return self._place_order("TTTC0012U", stock_code, quantity, price, "00")

    def place_sell_order(self, stock_code: str, quantity: int, price: int) -> Dict:
        # NOTE: 현재 미사용 (향후 지정가 주문 필요시 사용)
        logger.info(f"📉 [SELL] 지정가 매도 주문: {stock_code} {quantity}주 @{price:,}원")
        return self._place_order("TTTC0011U", stock_code, quantity, price, "00")

    def place_sell_order_market(self, stock_code: str, quantity: int) -> Dict:
        logger.info(f"📉 [SELL_MARKET] 시장가 매도 주문: {stock_code} {quantity}주")
        return self._place_order("TTTC0801U", stock_code, quantity, 0, "01")

    def place_buy_order_market(self, stock_code: str, quantity: int) -> Dict:
        logger.info(f"📈 [BUY_MARKET] 시장가 매수 주문: {stock_code} {quantity}주")
        return self._place_order("TTTC0802U", stock_code, quantity, 0, "01")

    def get_volume_ranking(self, count: int = 20) -> List[Dict]:
        """거래량 순위 조회 (v2: 데이터 파싱 로직 복원)"""
        try:
            logger.info(f"📊 [VOLUME] 거래량 순위 조회 시작 (상위 {count}개)")
            
            # NOTE: FID_TRGT_EXLS_CLS_CODE는 주요 제외 조건을 설정하는 중요한 파라미터입니다.
            # 현재 "100001011"로 설정되어 관리종목, 거래정지, 우선주, ETF/ETN을 제외합니다.
            # 이 값은 필요에 따라 설정 파일 등으로 관리하여 유연하게 변경할 수 있습니다.
            params = {
                "FID_COND_MRKT_DIV_CODE": "J",          # J: 전체 (코스피+코스닥)
                "FID_COND_SCR_DIV_CODE": "20171",       # 조건 화면 분류 코드
                "FID_INPUT_ISCD": "0000",               # 입력 종목 코드 (전체)
                "FID_DIV_CLS_CODE": "0",                # 구분 분류 코드 (0: 전체)
                "FID_BLNG_CLS_CODE": "0",               # 소속 분류 코드 (0: 전체)
                "FID_TRGT_CLS_CODE": "111111111",       # 대상 구분 (전부 포함)
                # 제외 대상 구분 (9자리 문자열, 1로 설정 시 제외)
                # 1: 관리종목, 2: 투자경고/위험, 3: 투자주의, 4: 불성실공시, 5: 단기과열
                # 6: 거래정지, 7: 정리매매, 8: 우선주, 9: ETF/ETN
                "FID_TRGT_EXLS_CLS_CODE": "100001011", # 관리종목, 거래정지, 우선주, ETF/ETN 제외
                "FID_INPUT_PRICE_1": "",                # 가격 조건 (없음)
                "FID_INPUT_PRICE_2": "",                # 가격 조건 (없음)
                "FID_VOL_CNT": "",                      # 거래량 조건 (없음)
                "FID_INPUT_DATE_1": ""                  # 날짜 조건 (없음)
            }
            data = self.api.request("volume_rank", params=params)
            
            if not (data and data.get("rt_cd") == "0"):
                return []

            volume_stocks = []
            for i, stock in enumerate(data.get("output", [])[:count]):
                try:
                    stock_code = stock.get('mksc_shrn_iscd', '').zfill(6)
                    stock_name = stock.get('hts_kor_isnm', '')
                    current_price = int(stock.get('stck_prpr', 0) or 0)
                    
                    if not (stock_code and stock_name and current_price > 0):
                        continue

                    stock_info = {
                        'code': stock_code,
                        'name': stock_name,
                        'current_price': current_price,
                        'change_rate': float(stock.get('prdy_ctrt', 0) or 0),
                        'volume': int(stock.get('acml_vol', 0) or 0),
                        'volume_rank': i + 1,
                        'volume_turnover': int(stock.get('acml_tr_pbmn', 0) or 0),
                    }
                    volume_stocks.append(stock_info)
                except (ValueError, TypeError) as e:
                    logger.warning(f"⚠️ [VOLUME] 종목 데이터 파싱 실패: {stock.get('hts_kor_isnm', 'Unknown')} - {e}")
                    continue
            
            logger.info(f"✅ [VOLUME] 거래량 순위 {len(volume_stocks)}개 파싱 완료")
            return volume_stocks

        except Exception as e:
            logger.error(f"❌ [VOLUME] 거래량 순위 조회 오류: {e}")
            return []

    def get_stock_price(self, stock_code: str) -> Dict:
        """종목 현재가 조회"""
        try:
            params = {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": stock_code.lstrip('A').zfill(6)
            }
            data = self.api.request("get_price", params=params)
            if data and data.get("rt_cd") == "0":
                return data.get("output", {})
            return {}
        except Exception as e:
            logger.error(f"❌ [PRICE] {stock_code} 현재가 조회 오류: {e}")
            return {}

    def get_total_assets(self) -> int:
        """현재 총 자산(현금 + 주식 평가액)을 API를 통해 직접 조회합니다."""
        try:
            # logger.info("💰 [ASSETS] 총 자산 조회를 시작합니다...")
            cash_balance = self.get_simple_balance()
            positions = self.get_current_positions()
            
            stock_eval_balance = 0
            if positions:
                stock_eval_balance = sum(int(p.get('evlu_amt', 0)) for p in positions)
                # logger.info(f"✅ [ASSETS] 주식 평가액: {stock_eval_balance:,.0f}원 ({len(positions)} 종목)")
            
            total_assets = cash_balance + stock_eval_balance
            logger.info(f"✅ [ASSETS] API 조회 총 자산: {total_assets:,.0f}원 (현금: {cash_balance:,.0f}원 + 주식: {stock_eval_balance:,.0f}원)")
            return total_assets
        except Exception as e:
            logger.error(f"❌ [ASSETS] 총 자산 조회 중 예외 발생: {e}", exc_info=True)
            return 0

def init_account_manager(app_key: str, app_secret: str, account_no: str):
    """계정 관리자 초기화"""
    return KISAccountManager(app_key, app_secret, account_no)

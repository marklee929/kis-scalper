"""
KIS API 계정 관리자 (v3: Limit-then-Market 로직 추가)
"""
import time
from typing import Dict, List, Optional
import logging
from api.kis_api import KISApi

logger = logging.getLogger(__name__)

class OrderResult:
    def __init__(self, ok: bool, order_id: Optional[str], filled_qty: int, msg: str = ""):
        self.ok = ok
        self.order_id = order_id
        self.filled_qty = filled_qty
        self.msg = msg

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
                "PDNO": "",
                "ORD_DVSN": "01",
                "ORD_UNPR": "0",
                "ORD_QTY": "0",
                "CMA_EVLU_AMT_ICLD_YN": "N",
                "OVRS_ICLD_YN": "N"
            }
            data = self.api.request("get_balance", params=params)
            if data and data.get("rt_cd") == "0":
                output_data = data.get("output", {})
                available_cash = int(output_data.get("nrcvb_buy_amt", 0))
                return available_cash
            return 0
        except Exception:
            return 0

    def get_current_positions(self) -> List[Dict]:
        """현재 보유 종목 조회"""
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
                "ORD_DVSN": order_type,
                "ORD_QTY": str(int(quantity)),
                "ORD_UNPR": str(int(price))
            }
            headers = {"tr_id": tr_id}
            data = self.api.request("order_cash", body=body, headers=headers)
            success = data and data.get("rt_cd") == "0"
            return {
                "success": success,
                "error": (data.get("msg1") if (data and not success) else ""),
                "order_id": (data.get("output", {}).get("ODNO", "") if data else ""),
                "full_response": (data or {})
            }
        except Exception as e:
            logger.error(f"❌ [ORDER] 주문 실행 오류: {e}")
            return {"success": False, "error": str(e), "order_id": ""}

    def place_limit_buy_order(self, stock_code: str, quantity: int, price: int) -> Dict:
        logger.info(f"📈 [BUY-LIMIT] 지정가 매수 주문: {stock_code} {quantity}주 @{price:,}원")
        return self._place_order("TTTC0802U", stock_code, quantity, price, "00")

    def place_sell_order_market(self, stock_code: str, quantity: int) -> Dict:
        logger.info(f"📉 [SELL-MARKET] 시장가 매도 주문: {stock_code} {quantity}주")
        return self._place_order("TTTC0801U", stock_code, quantity, 0, "01")

    def place_buy_order_market(self, stock_code: str, quantity: int) -> Dict:
        logger.info(f"📈 [BUY-MARKET] 시장가 매수 주문: {stock_code} {quantity}주")
        return self._place_order("TTTC0802U", stock_code, quantity, 0, "01")

    def has_open_order(self, stock_code: str) -> bool:
        """특정 종목에 대한 미체결 주문이 있는지 확인합니다."""
        try:
            open_orders = self.api.inquire_cancellable_orders()
            if open_orders and open_orders.get("rt_cd") == "0":
                for order in open_orders.get("output1", []):
                    if order.get("pdno") == stock_code.lstrip('A').zfill(6):
                        return True
            return False
        except Exception as e:
            logger.error(f"[OPEN_ORDER] {stock_code} 미체결 주문 조회 오류: {e}")
            return False

    def get_filled_qty(self, order_id: str) -> int:
        """주문 ID로 체결 수량을 조회합니다."""
        try:
            details = self.api.get_order_details(order_id)
            if details:
                return int(details.get('tot_ccld_qty', 0))
            return 0
        except Exception as e:
            logger.error(f"[FILLED_QTY] {order_id} 체결 수량 조회 오류: {e}")
            return 0

    def cancel_order(self, order_id: str) -> bool:
        """주문 ID로 주문을 취소합니다."""
        try:
            order_details = self.api.get_order_details(order_id)
            if not order_details:
                logger.warning(f"[CANCEL] 취소할 주문({order_id}) 정보를 찾을 수 없습니다.")
                return False
            result = self.api.cancel_order(order_details)
            if result and result.get("rt_cd") == "0":
                logger.info(f"[CANCEL] 주문 취소 성공: {order_id}")
                return True
            else:
                logger.error(f"[CANCEL] 주문 취소 실패: {order_id}, 응답: {result}")
                return False
        except Exception as e:
            logger.error(f"[CANCEL] {order_id} 주문 취소 중 오류: {e}")
            return False

    def place_buy_with_limit_then_market(
        self,
        stock_code: str,
        quantity: int,
        limit_price: float,
        check_wait_sec: float = 1.5,
        max_wait_sec: float = 3.0,
        poll_interval: float = 0.2,
    ) -> OrderResult:
        # 1) 지정가 1회 시도
        limit_res = self.place_limit_buy_order(stock_code, quantity, int(limit_price))
        if not limit_res.get('success') or not limit_res.get('order_id'):
            logger.warning(f"[LTM-BUY] {stock_code} 지정가 주문 실패, 즉시 시장가로 전환.")
            market_res = self.place_buy_order_market(stock_code, quantity)
            return OrderResult(market_res.get('success'), market_res.get('order_id'), 0, "LIMIT_FAIL_TO_MARKET")

        order_id = limit_res['order_id']
        start = time.time()

        # 2) 짧은 시간 동안 체결 확인
        while time.time() - start < check_wait_sec:
            filled = self.get_filled_qty(order_id)
            if filled >= quantity:
                return OrderResult(True, order_id, filled, "LIMIT_FILLED_FAST")
            time.sleep(poll_interval)

        # 3) 추가 대기
        while time.time() - start < max_wait_sec:
            filled = self.get_filled_qty(order_id)
            if filled >= quantity:
                return OrderResult(True, order_id, filled, "LIMIT_FILLED_SLOW")
            time.sleep(poll_interval)

        # 4) 부분 체결 또는 미체결 처리
        filled = self.get_filled_qty(order_id)
        remaining = max(0, quantity - filled)

        try:
            self.cancel_order(order_id)
        except Exception as e:
            logger.error(f"[LTM-BUY] {order_id} 지정가 주문 취소 실패: {e}")

        if remaining > 0:
            logger.info(f"[LTM-BUY] {stock_code} 지정가 미체결(잔량:{remaining}), 시장가로 전환.")
            market_res = self.place_buy_order_market(stock_code, remaining)
            # 시장가 주문 후 체결량 확인 로직은 복잡성을 가중시키므로, 여기서는 API 응답을 신뢰함
            return OrderResult(market_res.get('success'), market_res.get('order_id'), filled, "PARTIAL_TO_MARKET")
        else:
            return OrderResult(True, order_id, filled, "LIMIT_FILLED_BEFORE_CANCEL")

    def get_volume_ranking(self, count: int = 20) -> List[Dict]:
        """거래량 순위 조회 (v2: 데이터 파싱 로직 복원)"""
        try:
            logger.info(f"📊 [VOLUME] 거래량 순위 조회 시작 (상위 {count}개)")
            params = {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_COND_SCR_DIV_CODE": "20171",
                "FID_INPUT_ISCD": "0000",
                "FID_DIV_CLS_CODE": "0",
                "FID_BLNG_CLS_CODE": "0",
                "FID_TRGT_CLS_CODE": "111111111",
                "FID_TRGT_EXLS_CLS_CODE": "100001011",
                "FID_INPUT_PRICE_1": "",
                "FID_INPUT_PRICE_2": "",
                "FID_VOL_CNT": "",
                "FID_INPUT_DATE_1": ""
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

    def get_turnover_ranking(self, count: int = 20) -> List[Dict]:
        """거래대금 순위 조회"""
        try:
            logger.info(f"📊 [TURNOVER] 거래대금 순위 조회 시작 (상위 {count}개)")
            params = {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_COND_SCR_DIV_CODE": "20172", # 거래대금 순위
                "FID_INPUT_ISCD": "0000",
                "FID_DIV_CLS_CODE": "0",
                "FID_BLNG_CLS_CODE": "0",
                "FID_TRGT_CLS_CODE": "111111111",
                "FID_TRGT_EXLS_CLS_CODE": "100001011",
                "FID_INPUT_PRICE_1": "",
                "FID_INPUT_PRICE_2": "",
                "FID_VOL_CNT": "",
                "FID_INPUT_DATE_1": ""
            }
            data = self.api.request("volume_rank", params=params) # endpoint는 동일
            if not (data and data.get("rt_cd") == "0"):
                return []
            
            turnover_stocks = []
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
                        'turnover_rank': i + 1, # 거래대금 순위
                        'turnover': int(stock.get('acml_tr_pbmn', 0) or 0), # 누적 거래대금
                    }
                    turnover_stocks.append(stock_info)
                except (ValueError, TypeError) as e:
                    logger.warning(f"⚠️ [TURNOVER] 종목 데이터 파싱 실패: {stock.get('hts_kor_isnm', 'Unknown')} - {e}")
                    continue
            logger.info(f"✅ [TURNOVER] 거래대금 순위 {len(turnover_stocks)}개 파싱 완료")
            return turnover_stocks
        except Exception as e:
            logger.error(f"❌ [TURNOVER] 거래대금 순위 조회 오류: {e}")
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
            cash_balance = self.get_simple_balance()
            positions = self.get_current_positions()
            stock_eval_balance = 0
            if positions:
                stock_eval_balance = sum(int(p.get('evlu_amt', 0)) for p in positions)
            total_assets = cash_balance + stock_eval_balance
            logger.info(f"✅ [ASSETS] API 조회 총 자산: {total_assets:,.0f}원 (현금: {cash_balance:,.0f}원 + 주식: {stock_eval_balance:,.0f}원)")
            return total_assets
        except Exception as e:
            logger.error(f"❌ [ASSETS] 총 자산 조회 중 예외 발생: {e}", exc_info=True)
            return 0

def init_account_manager(app_key: str, app_secret: str, account_no: str):
    """계정 관리자 초기화"""
    return KISAccountManager(app_key, app_secret, account_no)
📄 gemini.md – Swing 종목 선정 개선안
🎯 목적

기존 거래량 순위 기반 필터(40~70위 등) 한정에서 벗어나,

전체 종목에서 잠잠하다가 순간 폭발하는 패턴을 실시간으로 잡아내는 로직으로 개선.

스윙 종목은 단순히 “많이 오른 주식”이 아니라, 상승 전환 + 체결강도 동반 + 거래량 폭발 조건 충족 시 진입 후보로 선정.

⚙️ 개선 핵심 로직
1. 전체 종목 대상 1차 필터

ETF/ETN/우선주/잡주 제외 (기존 EXCLUDE_KEYWORDS 유지)

거래대금 10억 이상 종목만 남기기 → 유동성 확보

2. 실시간 거래량 변화율 (ΔVolume)

최근 1분 거래량 / 직전 5분 평균 거래량 ≥ 3배 이상

단순 거래량 순위가 아닌, 폭발률 기반 점수 계산

지연 없이 즉각 후보 리스트에 추가

3. 체결강도 & 호가 비율 확인

체결강도 ≥ 120% 이상 (매수 우위)

매수호가 잔량 / 매도호가 잔량 ≥ 1.2

4. 가격 추세 필터

현재가 / 직전 5분 저가 ≥ +1% 이상 상승

고점대비 괴리율 ≤ 2% (너무 고평가된 종목 제외)

5. 점수화 스키마

ΔVolume 폭발률: 0~50점

체결강도: 0~30점

상승률(단기 추세): 0~20점

총점 ≥ 70점 → 스윙 후보 등록

📊 동작 시나리오

장 시작 5분 이후, 전체 종목 WebSocket 구독 시작

30초마다 거래량/체결강도/가격변화 체크

위 점수 기준 충족 종목만 logs/swing_candidates_YYYY-MM-DD.json 저장

모니터링 루프에서 최종 5~10개 종목만 남김

🛠️ 구현 구조 (예시)

strategies/swing_filter.py

def swing_stock_filter(market_cache, candidates, api):
    """스윙 적합 종목 필터링"""
    results = []
    for stock in candidates:
        code = stock["code"]
        name = stock.get("name", "")
        # 1️⃣ ETF/잡주 제외
        if any(k in name for k in EXCLUDE_KEYWORDS):
            continue
        # 2️⃣ 거래량 변화율
        vol_ratio = calc_volume_ratio(code, market_cache)
        if vol_ratio < 3: 
            continue
        # 3️⃣ 체결강도
        strength = get_strength(code, market_cache)
        if strength < 120: 
            continue
        # 4️⃣ 상승 전환
        if not is_price_breakout(code, market_cache):
            continue
        results.append(stock)
    return results


logs/swing_candidates_YYYY-MM-DD.json 저장 후 main.py에서 구독 업데이트

🚀 기대 효과

단순 순위 컷 제한(40~70위)을 없애고,

“잠잠하다가 순간 치는” 종목을 실시간 포착 가능

스윙 전략에서 폭발 구간 초입 진입 확률 증가

불필요한 잡주/테마주 제외로 승률 안정성 강화

👉 이 문서를 기준으로 score_monitor + swing_filter 두 갈래로 나눠서 관리 가능.
하나는 단타/스캘핑용 (score_monitor), 하나는 스윙용 (swing_filter).

## 추가 요청.. 자동화 

스윙 후보에서 ETF/ETN/인버스/레버리지 최대한 제거

매수 시 “1회 지정가 시도 → 미체결이면 즉시 예약 취소 후 시장가”

1) 스윙 후보 ETF 제외 필터
설정에 키워드/정규식 추가

config.json (또는 로딩되는 config dict)에 넣어둬.

{
  "trading": {
    "exclude_keywords": [
      "ETF","ETN","인버스","레버리지","선물","합성",
      "KODEX","TIGER","ARIRANG","HANARO","KBSTAR","KOSEF",
      "KINDEX","SOL","SMART","TRUE","FOCUS"
    ],
    "exclude_regex": [
      "(?i)\\bETF\\b",
      "(?i)\\bETN\\b",
      "(?i)인버스",
      "(?i)레버리지",
      "(?i)선물",
      "(?i)합성"
    ]
  }
}

스윙 스크리너 필터 함수
import re

def is_etf_like(name: str, symbol: str, trading_conf: dict) -> bool:
    if not name:
        return False
    nk = name.upper()
    # 1) 키워드 매칭
    for kw in trading_conf.get("exclude_keywords", []):
        if kw.upper() in nk:
            return True
    # 2) 정규식 매칭
    for rx in trading_conf.get("exclude_regex", []):
        if re.search(rx, name):
            return True
    # 3) 심볼 패턴(국내 ETN 종종 'B'표기 등 케이스가 있어 후방 안전장치로)
    if symbol and any(tag in symbol.upper() for tag in ["ETF","ETN"]):
        return True
    return False

스윙 후보 산출 시 적용
def get_swing_candidates(volume_stocks: list, config: dict) -> list:
    trading_conf = config.get("trading", {})
    n = len(volume_stocks)
    if n < 30:
        return []
    if n >= 70:
        cand_raw = volume_stocks[39:70]
    else:
        # 30~69개일 땐 하위 40%
        start = max(0, int(n * 0.6))
        cand_raw = volume_stocks[start:]

    # ETF/ETN/인버스/레버리지 제거
    filtered = []
    for s in cand_raw:
        name = s.get("name") or s.get("stock_name") or ""
        symbol = s.get("code") or s.get("symbol") or ""
        if not is_etf_like(name, symbol, trading_conf):
            filtered.append(s)
    return filtered


참고: 후보 출력 직전에도 한 번 더 is_etf_like() 걸어줘. 상위 로직에서 다른 경로로 들어온 리스트에도 안전.

2) 매수 로직: “1회 지정가 → 실패 시 시장가”

브로커별 API가 달라서 추상화 레벨로 줬어. 너희 OrderExecutor/kis_client/kiwoom 어디에든 쉽게 이식 가능.

import time
from typing import Optional

class OrderResult:
    def __init__(self, ok: bool, order_id: Optional[str], filled_qty: int, msg: str = ""):
        self.ok = ok
        self.order_id = order_id
        self.filled_qty = filled_qty
        self.msg = msg

class Broker:
    # 여기는 네 기존 래퍼에 맞춰 연결
    def place_limit_buy(self, symbol: str, qty: int, limit_price: float) -> OrderResult: ...
    def place_market_buy(self, symbol: str, qty: int) -> OrderResult: ...
    def cancel_order(self, order_id: str) -> bool: ...
    def get_filled_qty(self, order_id: str) -> int: ...

def place_buy_with_limit_then_market(
    broker: Broker,
    symbol: str,
    qty: int,
    limit_price: float,
    check_wait_sec: float = 1.5,
    max_wait_sec: float = 3.0,
    poll_interval: float = 0.2,
) -> OrderResult:
    # 1) 지정가 1회 시도
    r = broker.place_limit_buy(symbol, qty, limit_price)
    if not r.ok or not r.order_id:
        # 지정가 발주 자체가 실패하면 곧바로 시장가
        return broker.place_market_buy(symbol, qty)

    start = time.time()
    # 2) 아주 짧게 체결 확인(예약 성공 여부 + 체결여부)
    while time.time() - start < check_wait_sec:
        filled = broker.get_filled_qty(r.order_id)
        if filled >= qty:
            return OrderResult(True, r.order_id, filled, "LIMIT_FULLFILLED_FAST")
        time.sleep(poll_interval)

    # 3) 추가 대기(최대 max_wait_sec) — 체결이 더딜 때
    while time.time() - start < max_wait_sec:
        filled = broker.get_filled_qty(r.order_id)
        if filled >= qty:
            return OrderResult(True, r.order_id, filled, "LIMIT_FULLFILLED_SLOW")
        time.sleep(poll_interval)

    # 4) 부분 체결이면 잔량만 시장가, 0이면 전체 시장가
    filled = broker.get_filled_qty(r.order_id)
    remaining = max(0, qty - filled)

    # 지정가 예약 취소
    try:
        broker.cancel_order(r.order_id)
    except Exception:
        # 취소 실패해도 남은 수량은 시장가로 시도 (중복 체결 리스크는 브로커 단 방어)
        pass

    if remaining > 0:
        m = broker.place_market_buy(symbol, remaining)
        # 원한다면 체결 결과를 합산해서 리턴
        return OrderResult(m.ok, m.order_id, filled + m.filled_qty, "LIMIT_PARTIAL_CANCELLED_TO_MARKET")
    else:
        return OrderResult(True, r.order_id, filled, "LIMIT_FILLED_BEFORE_CANCEL")

사용 예
# ETF 방지 마지막 가드
name = quote.get("name","")
code = quote.get("code","")
if is_etf_like(name, code, config.get("trading", {})):
    logger.info(f"[BLOCK] ETF-like filtered on order: {code} {name}")
    return

# 지정가 한 번 시도 후 시장가 백업
best_ask = orderbook.best_ask(code)  # 네가 갖고 있는 호가 객체 사용
limit_price = round(best_ask * 1.001, 2)  # 살짝 위로(체결 유도)

res = place_buy_with_limit_then_market(broker, code, qty=buy_qty, limit_price=limit_price)
logger.info(f"[ORDER] buy result: ok={res.ok} filled={res.filled_qty} msg={res.msg}")

포인트

**“1회 지정가”**를 엄밀히 보장(재시도 없음).

부분체결이면 잔량만 시장가로 보충.

취소→시장가 순서에서, 취소 실패 예외가 나도 시장가로 진행(브로커 중복체결 방지 옵션에 의존).

체결 확인 대기는 짧게(1.5~3초) — 호가 얇은 장초에도 응답성 확보.

마지막 안전장치

선정 단계와 주문 직전 단계 모두에서 is_etf_like()를 적용(이중필터).

텔레그램 알림에 “ETF-필터로 제외” 메시지 찍기.

브로커별 ‘시장가’ 표기(키움/한국투자)는 내부 래퍼에서 통일(ORDER_TYPE.MARKET)로 처리.
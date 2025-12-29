# Event Types Mapping (KIS → Internal)

모든 외부 이벤트는
내부 표준 이벤트로 변환된다.

## Market Data
- KIS 체결 → TICK
- KIS 호가 → ORDERBOOK
- REST 현재가 → PRICE_SNAPSHOT
- 분봉/초봉 → BAR

## Trading
- 주문 요청 → ORDER_REQUEST
- 주문 접수 → ORDER_ACK
- 체결 → FILL
- 취소/정정 → CANCEL_ACK

## Account
- 잔고 조회 → BALANCE_UPDATE
- 포지션 변경 → POSITION_UPDATE

## News
- 뉴스 수집 → NEWS_SIGNAL

## System
- WS 연결/해제 → HEARTBEAT
- API 오류 → ERROR
- 지연 초과 → LATENCY_ALERT

### Principle
- 외부 이벤트는 절대 전략으로 직접 가지 않는다
- 반드시 event_loop → snapshot → entity 순서

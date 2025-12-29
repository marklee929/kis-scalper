# Event Loop Spec (Single Source of Truth)

핵심 원칙:
- 계좌/포지션/주문/체결 상태를 바꾸는 주체는 단 하나여야 한다.
- “체결/잔고 업데이트”는 반드시 단일 이벤트 루프에서만 수행한다.
- 전략(Entity)은 상태를 바꾸지 않고 “제안”만 한다.

## Components
- MarketDataIngestor (WS/REST)
- OrderManager (place/modify/cancel)
- PortfolioState (positions, cash, exposure)
- RiskGate (hard constraints)
- EntityRouter (snapshot broadcast)
- ExecutionSimulator (paper / sim fill)
- Logger (evolution logs)
- ControlPlane (halt/resume)

## Event Types
- TICK (실시간 체결/호가)
- BAR (1s/5s/1m 집계 스냅샷)
- ORDER_ACK
- FILL (체결)
- CANCEL_ACK
- BALANCE_UPDATE
- NEWS_SIGNAL
- HEARTBEAT
- ERROR (API, parse, disconnect)

## Main Loop
1) ingest event
2) update internal state (ONLY HERE)
3) build snapshot (immutable)
4) broadcast snapshot to entities (read-only)
5) collect proposals (action, confidence, size)
6) pass proposals through RiskGate
7) execute (paper/sim/real)
8) log everything

## Concurrency Rule
- Ingestor는 멀티스레드 가능
- BUT 상태 변경은 큐를 통해 event_loop 1개 스레드로만

## Snapshot Contract
- snapshot은 불변 객체
- entity는 snapshot을 참조만 가능
- snapshot 생성 시점/버전/시드(재현성) 포함

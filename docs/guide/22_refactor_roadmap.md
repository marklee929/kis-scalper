# Refactor Roadmap (kis_scalper Remodeling)

목표:
- “돌아가는 것”을 먼저 만든다
- 그 다음 “죽지 않게” 만든다
- 마지막으로 “진화”시킨다

## Phase 0: Freeze & Baseline
- 현재 kis_scalper 상태를 태그/브랜치로 고정
- 페이퍼 운용이 최소 1일 돌아가게 유지

## Phase 1: Environment Skeleton
- 단일 이벤트 루프 도입
- PortfolioState / OrderManager / Logger 최소 구현
- REST/WS 입력을 event로 변환해서 큐에 넣기

Success:
- 실시간 스냅샷이 주기적으로 생성됨
- 주문/체결/잔고가 “단일 루프”에서만 변함

## Phase 2: RiskGate (DNA) 먼저
- MaxLoss / MaxExposure / Cooldown / API Health
- “죽는 상황”에서 자동으로 멈추는지 확인

Success:
- 일부러 에러/지연/슬리피지 시나리오 넣어도 시스템이 멈추고 로그 남김

## Phase 3: Entities (3 Presets)
- A: Momentum, B: Reversion, C: Survival
- 인터페이스 통일(propose only)

Success:
- 같은 스냅샷에서 3개가 동시에 제안
- Gate 이후 실행/비실행이 기록됨

## Phase 4: Shadow Mode + Promotion
- 신규 개체는 무조건 OBSERVE/SHADOW로 시작
- 승격 규칙 적용

Success:
- 장중에도 “안전하게” 교체 가능

## Phase 5: Offline Evolution
- 장후 스코어링
- 파라미터 미세 조정
- 동면/봉인 기록

Success:
- 다음날 파라미터가 소폭 반영되고, 실패가 반복되면 봉인됨

## Phase 6: Dashboard
- 시스템 건강도 / 레짐 / 개체 상태 / 사망 원인
- 감정 유발 UI 금지

Success:
- “왜 멈췄는지”를 10초 안에 설명 가능

# Risk Gate Spec (DNA)

RiskGate는 전략이 아니라 “기관”이다.
학습 대상이 아니며, 하드 룰로 박는다.

## Inputs
- portfolio_state
- proposed_action
- market_snapshot
- system_health
- news_signal

## Outputs
- ALLOW / DENY
- ALLOW_WITH_MODIFICATION (size 축소, 주문타입 변경 등)
- HALT (멸망 트리거 또는 심각 이상)

## Hard Constraints (최소 세트)
1) Max Daily Loss
- 당일 손실이 임계값 초과 시: 신규 매수 금지 + 청산만 허용

2) Max Exposure
- 계좌 대비 총 노출(현금 포함) 상한
- 종목 단일 노출 상한

3) Cooldown
- 손절/연속손실 이후 일정 시간 신규 진입 금지

4) Slippage Guard
- 예상 슬리피지(스프레드/호가) 급증 시 size 자동 축소 또는 거래 금지

5) Liquidity Guard
- 거래대금/호가 잔량이 기준 미달이면 거래 금지

6) API Health Guard
- WS 끊김/REST 에러율 증가/지연 증가 시 risk_off

7) News Severity Veto
- severity가 임계 이상이면:
  - 신규 진입 금지
  - 기존 포지션 축소 또는 관찰 모드

## Principle
- Gate는 “이길 확률”이 아니라 “죽을 확률”을 줄인다.
- 전략이 아무리 좋은 제안을 해도 Gate가 거르면 끝.

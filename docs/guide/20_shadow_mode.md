# Shadow Mode (승격 전 그림자 운용)

Shadow Mode 목적:
- 모델 교체를 “사고”가 아니라 “승격 절차”로 만든다.

## Modes
1) ACTIVE
- 실제 주문 권한 있음

2) SHADOW
- 주문 권한 없음
- 동일 스냅샷에서 가상 주문만 수행
- 성과/사망/비용을 동일 기준으로 로그

3) OBSERVE (Warm-up)
- 일정 기간은 제안조차 하지 않고 내부 상태만 채움
- (특히 레짐/지표 누적이 필요한 모델)

## Promotion Rule (예시)
- OBSERVE: 30~60분 또는 N 스냅샷
- SHADOW: 최소 1~3일
- 조건:
  - 사망률 낮음
  - MDD 제한 만족
  - 거래비용 민감도 허용
  - 레짐별 성능 편향 확인

## Demotion Rule
- ACTIVE라도 사망/연속손실 발생 시
  - 즉시 SHADOW 또는 OBSERVE로 강등 가능

핵심:
- “교체”가 아니라 “권한 부여/회수”로 관리한다.

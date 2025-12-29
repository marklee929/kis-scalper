# Incident Response Runbook

사고는 반드시 발생한다.
중요한 것은 대응이 아니라 순서다.

## Incident Types

### A. API 장애
Trigger:
- WS disconnect 지속
- REST 에러율 급증

Action:
- 시스템 자동 risk_off
- 신규 주문 금지
- 관찰 모드 유지

Human:
- 아무것도 하지 않음
- 복구 후 자동 재개 확인

---

### B. 연속 사망 발생
Trigger:
- 동일 레짐에서 사망 N회 초과

Action:
- 해당 개체 자동 봉인
- Shadow 이하로 강등

Human:
- 봉인 사유 확인
- 즉각 해제 금지

---

### C. 멸망 트리거
Trigger:
- 다중 세대 동시 사망
- 체결 물리 붕괴
- 규제/시장 구조 변화 감지

Action:
- 전체 시스템 HALT
- 로그 고정
- 자동 재개 금지

Human:
- 로그 검토
- 환경 가정 재검증
- 수동 승인 후 재가동

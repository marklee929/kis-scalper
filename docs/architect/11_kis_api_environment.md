# KIS API as Environment

한투 API는 도구가 아니라
환경의 일부다.

설계 원칙:
- 모든 API는 Adapter로 감싼다
- 전략은 API를 직접 호출하지 않는다
- API 장애는 환경 재난이다

필수 Adapter:
- Auth (token / approval_key)
- Market Data (REST / WS)
- Order / Cancel / Modify
- Balance / Position
- Symbol Metadata

API 장애 시:
- 즉시 risk_off
- 신규 주문 금지
- 관찰 모드 유지
- 복구 후 재개

API는 신뢰 대상이 아니다.
환경의 일부일 뿐이다.

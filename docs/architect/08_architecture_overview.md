# Architecture Overview

본 시스템은 단일 언어/단일 프로세스를 지양한다.

핵심 원칙:
- 생존(실시간)과 진화(사고)는 분리된다
- 멈추지 말아야 할 것은 강한 언어로
- 자주 바뀌어야 할 것은 유연한 언어로

구조:

[ Java / Kotlin ]
- KIS API (REST + WebSocket)
- 실시간 시세 수신
- 주문 / 체결 / 잔고
- 리스크 게이트
- 가상계좌 환경
- 이벤트 큐 (단일 루프)

        ↓ snapshot / event

[ Python ]
- 전략(Entity) 로직
- 스코어링
- 진화 로직
- 뉴스 분류
- 장후 분석
- 세대/동면 관리

통신:
- Redis / ZeroMQ / gRPC 중 택1
- 동기 호출 금지, 이벤트 기반만 허용

Java는 숨을 쉬고
Python은 생각한다.

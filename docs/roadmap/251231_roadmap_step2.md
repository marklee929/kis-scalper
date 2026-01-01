KIS REST 토큰/웹소켓 approval key 발급/캐시 + 웹소켓 연결/구독/재구독/heartbeat/끊김 감지 로직을 구현해라.
- token_manager: secrets.json 또는 cache 파일에 만료시간 포함 저장
- ws_manager: asyncio 기반, reconnect backoff, 구독 종목 리스트 동적 갱신 지원
- tick_normalizer: raw message -> TickEvent로 표준화
실제 키 없이도 돌아가게 "mock websocket" 옵션도 추가해라.

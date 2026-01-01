너는 시니어 파이썬 퀀트/트레이딩 시스템 엔지니어다.
목표: KIS OpenAPI(REST + WebSocket)를 이용해 실시간 데이터를 수집/집계하고,
3개로 분리된 모델이 "가상매매(paper trading)" 환경에서 실시간으로 학습하며,
매수/매도 행동과 성과(수수료/슬리피지 포함)를 기록하는 v2 프레임워크를 구현해라.

중요 제약:
- v1 레거시 코드는 기능 참고만. v2는 새 프로젝트로 구성하되,
  v1의 KIS 접속/토큰/웹소켓 구독/재접속 로직은 "모듈로 재사용" 가능하면 그대로 가져와라.
- 외부 스크래핑/뉴스/RAG는 이번 범위에서 제외. 오로지 KIS 데이터 기반.
- 실거래는 하지 않는다. 무조건 가상매매(모의체결) 또는 KIS 모의투자 endpoint(가능하면 옵션)만 사용.
- 실시간 학습은 "안정적"이어야 한다: 끊김/재접속/토큰 갱신시에도 상태가 유지되고 로그가 남아야 한다.
- 모델은 3개(모멘텀/눌림목반등/변동성돌파)로 분리하고,
  각각 독립적으로 관측(observation)을 받아 행동(action)을 출력하며,
  동일한 시장 데이터 스트림을 공유하지만 학습/리워드/로그는 분리한다.

출력 결과물:
- 로컬에서 실행 가능한 파이썬 프로젝트(v2) 코드 전체
- 폴더 구조, 핵심 클래스/인터페이스, 실행 방법(README)
- 로그/데이터 저장 포맷 정의(JSONL 또는 Parquet/SQLite)
- 최소 동작 MVP: 1) 웹소켓 연결 2) 1초/1분 집계 3) 모델 3개가 관측 받고
  4) paper order 실행 5) PnL/리워드 계산 6) transition 로그 기록

언어/라이브러리:
- Python 3.12
- 추천: asyncio, websockets(or aiohttp), pydantic, pandas(optional), numpy
- 저장: SQLite(기본) + 옵션으로 Parquet
- 모델: 처음엔 룰 기반 + online 업데이트 가능한 간단한 밴딧/로지스틱/SGDClassifier 중 택1
  (무거운 딥러닝은 금지. 프레임워크 먼저)

반드시 포함할 설계 요소:
1) Connectivity Layer
   - token_manager: REST access_token + websocket approval key 관리(캐시 파일)
   - ws_manager: 구독/재구독/heartbeat/끊김 감지/자동 재연결
2) Market Data Layer
   - tick_normalizer: WS raw -> 표준 TickEvent
   - bar_aggregator: 1s, 1m OHLCV + 보조통계(변동성, 거래량 z-score)
   - feature_builder: 최근 N초/분 윈도우로 observation 생성
3) Paper Execution Layer
   - paper_broker: 주문/체결 시뮬레이션(시장가 기준, 슬리피지/수수료 반영)
   - portfolio: 포지션/현금/평단/미실현/실현손익
4) Env Layer (Realtime TradingEnv)
   - step(obs)->action->fill->reward->next_obs 를 구성
   - done 조건(장마감, max drawdown, max trades 등)
   - risk_guard: max position size, cooldown, spread 필터 등
5) Model Layer (3개)
   - BasePolicy 인터페이스: act(obs)->action
   - BaseLearner 인터페이스: update(transition)
   - MomentumPolicy/Learner
   - PullbackPolicy/Learner
   - VolBreakoutPolicy/Learner
   - 각 모델별 observation_view를 다르게 구성(mode_id 또는 builder 분기)
6) Logging
   - transition 로그: t, code, model_id, obs, action, fill, reward, next_obs, done, meta
   - 일별 summary: 총거래, 승률, 총수익/손실, MDD, 수수료, 슬리피지
   - 장애/재연결 로그

구현 순서(꼭 지켜라):
- Step A: 폴더/인터페이스/스키마 먼저 만든다
- Step B: ws 연결+수신->표준 이벤트 변환까지
- Step C: 1s/1m 집계 + feature_builder
- Step D: paper_broker + portfolio + reward 계산
- Step E: 모델 3개 stub(룰 기반)로 end-to-end 동작
- Step F: learner.update로 온라인 학습(간단한 확률/가중치 업데이트)
- Step G: README 및 실행 커맨드 제공

코드 품질:
- 타입힌트 필수
- 예외처리/재시도/로그 필수
- config.yaml 또는 config.py로 파라미터 관리
- 단위테스트는 선택, 대신 최소한의 시뮬레이션 실행 스크립트 포함

마지막으로:
- KIS WebSocket 메시지 타입별 파싱은 함수로 분리하고,
  나중에 종목 리스트 갱신(구독 종목 변경)이 가능하도록 설계해라.
- "실시간 학습"은 매 tick마다가 아니라 1초 또는 1분 배치로 update 하도록 하여 안정성을 확보해라.

이 지시를 기준으로 v2 코드를 생성해라.

모델별 observation_view 규칙:
- momentum: short_return(1s~30s), volume_z, orderbook_imbalance, breakout_flag 중심
- pullback: drawdown_from_high, mean_reversion_signal(zscore), recovery_slope 중심
- vol_breakout: realized_vol, vol_regime, range_breakout_signal 중심
각 view는 공통 base_features + view_features로 구성해라.

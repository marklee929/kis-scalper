# kis-scalper 전체 구조 및 주요 파일 역할 (2025-08-12 기준)

```
kis-scalper/
│
├── api/           # KIS REST 래퍼, endpoint catalog
├── auth/          # 토큰 발급/갱신, secrets.json 관리
├── web_socket/    # 실시간 WS 클라이언트, 구독/재연결/캐시
├── strategies/    # 워치리스트/점수/포지션/엔트리/익절 orchestration
├── tactics/       # 신호/리스크/스코어/볼륨/스파이크 등 pure 함수
├── trade/         # 주문 실행, 매수 엔진
├── utils/         # 로깅, 스케줄러, 텔레그램, 코드 로더, 안전 요청
├── state/         # 포지션 저장/조회
├── data/          # 일별 요약 XLSX
├── logs/          # 런타임 아티팩트(실적, 후보, 포지션, 요약)
├── config/        # secrets.json (인증정보)
├── main.py        # 전체 앱 부트스트랩
├── prompt/        # Copilot/팀원용 전체 맥락 파일
└── prefetch_watchlist.py # 사전 워치리스트 생성 스크립트
```

---

## 주요 모듈/파일 역할

- **main.py**: 전체 앱 부트스트랩, 토큰/워치리스트/스레드 관리
- **api/**: KIS REST API 래퍼, endpoint catalog
- **auth/**: 토큰 발급/갱신, secrets.json 관리
- **web_socket/**: 실시간 WS 클라이언트, 구독/재연결/캐시
- **strategies/**: 워치리스트 관리, 점수 계산, 포지션 모니터, 엔트리/익절 로직
- **tactics/**: 신호/리스크/스코어/볼륨/스파이크 등 pure 함수
- **trade/**: 주문 실행, 매수 엔진
- **utils/**: 로깅, 스케줄러, 텔레그램, 코드 로더, 안전 요청
- **state/**: 포지션 저장/조회
- **logs/**: 런타임 아티팩트(실적, 후보, 포지션, 요약)
- **config/**: secrets.json (인증정보)
- **data/**: 일별 요약 XLSX

---

## 전체 흐름 요약

1) main.py → secrets.json 로드 → 토큰 발급/갱신
2) 워치리스트 초기화(전일 sector_filtered or code_loader)
3) score_monitor 스레드 → 점수 계산/구독 갱신
4) WebSocket 클라이언트 → 실시간 체결/호가 수신
5) buy_engine/position_monitor → 엔트리/청산/주문 실행
6) logs/에 실적/후보/포지션 기록, 텔레그램 알림
7) 장 마감 후 요약/정산

---

## 실행 방법

```bash
python main.py
```
- secrets.json은 config/에 위치
- KIS OpenAPI 인증 필요(app_key, app_secret, account_no)

---

## 운영 팁

- rate limit: 1.2초/주문
- 주요 에러: 토큰 만료, WS 재연결, 주문 실패(rt_cd), 워치리스트 비어 있음
- logs/app.log에서 [ERROR], [score_monitor], [order], [WS] 등 키워드로 모니터링

---

## 확장/테스트

- tactics/에 pure 함수 추가 후 entry_filters.py에 연결
- strategies/score_monitor.py에서 score_threshold 조정으로 후보 수 튜닝
- logs/scored_candidates_YYYY-MM-DD.json에서 후보 리스트 확인

---

## 파일 목록 자동화

Windows PowerShell:
```powershell
Get-ChildItem -Recurse | Select-Object FullName
```
Linux/macOS:
```bash
find . -type f
```
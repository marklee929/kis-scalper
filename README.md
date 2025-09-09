<!-- filepath: c:\WORK\kis-scalper\README.md -->
# 💹 KIS-SCALPER

> 한국투자증권 OpenAPI 기반 초단타 자동매매 시스템  
> 실시간 호가/체결 데이터 수집부터 전략 실행, AI 예측까지 확장 가능한 구조

---

## 🚀 프로젝트 목표

- KIS Developers API를 활용한 **자동 스캘핑 매매 시스템**
- 실시간 데이터 수집 및 저장 (1초봉 / 체결강도 / 호가)
- 간단한 전략 기반 자동 주문 시스템 구현
- 향후 AI 강화학습 및 예측 시스템으로 확장 가능

---

## 🧱 현재 시스템 구조

```
├── api/                    # KIS API 연동
│   ├── kis_api.py         # REST API 클라이언트
│   └── api_endpoints.json # API 엔드포인트 정의
├── auth/                   # 토큰 관리
│   ├── token_manager.py   # access_token/approval_key 발급
│   └── token_refresher.py # 자동 토큰 갱신
├── web_socket/            # 실시간 데이터
│   ├── web_socket_manager.py # WebSocket 연결 관리
│   └── market_cache.py    # 실시간 체결가 캐시
├── strategies/            # 매매 전략
│   ├── score_monitor.py   # 실시간 모멘텀 분석
│   └── watchlist_shared.py # 동적 종목 관리
├── trade/                 # 주문 실행
│   ├── buy_engine.py      # 매수 엔진
│   └── position_monitor.py # 포지션 모니터링
├── utils/                 # 유틸리티
│   └── logger.py         # 로깅 시스템
└── config/               # 설정 파일
    ├── secrets.json      # API 키 설정
    └── *.json           # 토큰 상태 파일
```

### 🔄 핵심 플로우 (구현됨)

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  WebSocket  │───▶│ market_cache│───▶│score_monitor│
│ 실시간 체결가│    │   캐시 저장  │    │ 추세 분석    │
└─────────────┘    └─────────────┘    └─────────────┘
                                              │
                   ┌─────────────┐            │
                   │ 구독 해지    │◀───────────┤
                   │ (하락 종목)  │            │
                   └─────────────┘            │
                                              │
                   ┌─────────────┐            │
                   │ buy_engine  │◀───────────┘
                   │ 매수 실행    │ emit_buy()
                   └─────────────┘
```

### ✅ 현재 구현된 기능들

1. **실시간 데이터 수집**: WebSocket으로 체결가 실시간 캐시
2. **동적 종목 관리**: 하락 종목 구독 해지 + 상승 종목 추가  
3. **자동 토큰 관리**: access_token/approval_key 자동 갱신
4. **모멘텀 기반 매수**: 상승 추세 감지시 자동 매수 신호
5. **포지션 모니터링**: 실시간 손익 추적 및 자동 매도
6. **리소스 효율화**: 30개 종목 제한 모니터링

---

## 🎯 단타 전략 고도화 계획

> **현재 기본 구조가 탄탄하므로, 아래 기능들을 단계적으로 추가하여 시스템을 고도화**

### Phase 1: 진입/청산 로직 강화

```python
# 추가 예정: strategies/scalping_signals.py
- RSI, 볼린저밴드 기반 정교한 진입 신호
- 거래량 급증 감지 (체결강도 3배 이상)
- 호가 스프레드 모니터링
- 5틱 연속 상승 감지 등 마이크로 트렌드
```

```python
# 추가 예정: strategies/risk_management.py  
- 손절: -0.8% 고정
- 익절: +1.2% 고정
- 트레일링 스탑: 0.3%
- 시간 기반 청산: 최대 15분 보유
```

### Phase 2: 종목 선별 고도화

```python
# 추가 예정: strategies/stock_screener.py
- 거래량 기준 (10만주 이상)
- 변동성 기준 (일간 2% 이상)  
- 호가 스프레드 (0.3% 이하)
- 시가총액 (1천억 이상)
- 실시간 스코어링 시스템 (0-100점)
```

### Phase 3: 실시간 분석 확장

```python
# 추가 예정: web_socket/enhanced_processor.py
- 100틱 버퍼링으로 마이크로 트렌드 분석
- 연속 상승/하락 틱 감지
- 거래량 급증 실시간 알림
- 호가창 변화 모니터링
```

### Phase 4: 포지션 관리 최적화

```python
# 추가 예정: trade/position_sizer.py
- 계좌 대비 리스크 1.5% 고정
- 변동성 기반 포지션 조정
- 최대 포지션 제한 (계좌의 30%)
- 켈리 공식 기반 최적 사이징
```

### Phase 5: 시간대별 전략

```python
# 추가 예정: strategies/time_based_strategy.py
- 09:00-09:30: 장초반 갭상승 추격
- 10:30-11:00: 첫 조정 후 반등 포착
- 14:30-15:00: 장마감 전 스퍼트
- 뉴스/공시 실시간 연동
```

### Phase 6: 백테스팅 및 성과 분석

```python
# 추가 예정: analytics/
- 일일/주간/월간 수익률 추적
- 승률, 평균 손익비 계산  
- 최대 낙폭(MDD) 모니터링
- 전략 파라미터 자동 최적화
- 리포트 자동 생성
```

---

## 🛠️ 설치 및 실행

### 1. 환경 설정
```bash
# 의존성 설치
pip install -r requirements.txt

# 설정 파일 생성
cp config/secrets.json.example config/secrets.json
# secrets.json에 KIS API 키 입력
```

### 2. KIS API 설정
```json
{
  "APP_KEY": "발급받은_앱키",
  "APP_SECRET": "발급받은_시크릿",
  "ACCOUNT_NO": "계좌번호",
  "ENVIRONMENT": "PAPER",  // PAPER: 모의투자, REAL: 실전투자
  "CUSTTYPE": "P",         // P: 개인, B: 법인
  "BUDGET": "1000000"      // 투자 예산
}
```

### 3. 실행
```bash
python -m main
```

---

## 📊 모니터링 로그 예시

```
[2025-08-14 12:00:43] INFO  [INIT] 초기 watchlist 세팅 완료 (3종목)
[2025-08-14 12:00:43] INFO  🚀 WebSocket 연결 시도...
[2025-08-14 12:00:43] INFO  WebSocket 연결 성공
[2025-08-14 12:00:40] INFO  [score_monitor] 구독 +30 (rank 신규)
[2025-08-14 12:02:42] INFO  매수 엔진 스레드 시작
[2025-08-14 12:03:15] INFO  [BUY] 신호 수신: A005930 price=75000 momentum=8.5
[2025-08-14 12:03:15] INFO  [BUY] 매수 완료: A005930 1주 @75000
[2025-08-14 12:05:20] INFO  [SELL] 익절 매도: A005930 +1.2% 수익
```

---

## ⚠️ 주의사항

- **실전 투자 전 모의투자로 충분한 테스트 필수**
- 손절선 준수 및 리스크 관리 철저히
- API 호출 제한 (초당 20회) 준수
- 시장 상황에 따른 전략 파라미터 조정 필요

---

## 📈 향후 확장 계획

1. **머신러닝 통합**: 과거 데이터 기반 예측 모델
2. **멀티 전략**: 여러 전략 동시 운영 및 성과 비교
3. **포트폴리오 관리**: 섹터별 분산 투자
4. **실시간 대시보드**: 웹 기반 모니터링 UI
5. **알림 시스템**: 텔레그램/이메일 알림

---

## 🤝 기여하기

Pull Request와 Issue를 환영합니다!

## 📄 라이선스

MIT License

---

**⚡ 현재 상태: 기본 스캘핑 시스템 구현 완료 → Phase 1부터 고도화 진행 예정**

# 🚀 KIS 스캘핑 통합 시스템 v6.0

한국투자증권 API 기반 실시간 스캘핑 거래 시스템

## ⭐ Phase 1-6 통합 완료

- **Phase 1**: 실시간 신호 생성 
- **Phase 2**: 지능형 종목 선별
- **Phase 3**: 고도화된 포지션 관리  
- **Phase 4**: 시간대별 맞춤 전략
- **Phase 5**: 백테스팅 & 성과 분석
- **Phase 6**: 실시간 통합 운영

## 🚀 빠른 시작

```bash
# 1. 실행 파일로 시작 (권장)
run_trading_system.bat

# 2. Python 직접 실행
python main_integrated.py

# 3. 백테스트
python run_backtest.py
```

## 📁 프로젝트 구조

```
kis-scalper/
├── main_integrated.py     # 메인 실행
├── run_backtest.py       # 백테스트
├── strategies/           # 전략 모듈
├── trade/               # 거래 관리  
├── analytics/           # 성과 분석
└── logs/               # 결과 로그
```

## ⚠️ 설정 필요

1. KIS API 키 설정
2. 계좌 정보 입력  
3. 리스크 파라미터 조정

---
**v6.0 Complete Edition** 🎉

---

## 🔧 최근 디버깅 및 구조 개선 (2025-08-22)

장시간에 걸친 디버깅을 통해 시스템의 여러 잠재적 오류를 수정하고 안정성을 크게 향상했습니다.

### 주요 해결 문제

- **실시간 매도 로직 미동작**: 보유 종목의 현재가를 조회하지 못해 매도 로직이 실행되지 않던 문제를 해결했습니다.
    - 원인: `MarketCache` 중복 생성, 종목 코드 형식 불일치(Zero-padding, 'A' 접두어), 구독 요청 오류 등 복합적인 문제였습니다.
    - 해결: `MarketCache`를 단일 인스턴스로 관리하고, 모든 모듈이 이를 공유하도록 구조를 변경했습니다. 종목 코드 정규화 로직을 통일하고, API 호출 실패 시 2차 조회 로직을 추가하여 안정성을 높였습니다.
- **실시간 매수 로직 오류**: 웹소켓을 통해 들어오는 실시간 체결가 기반 매수 주문이 실패하던 문제를 해결했습니다.
    - 원인: 잘못된 파라미터 타입(가격), `AccountManager` 초기화 순서 오류, 잔고 관리 로직 부재 등.
    - 해결: `BalanceManager`를 도입하여 파일 기반으로 잔고를 관리하고, 모든 매수/매도 로직이 이를 참조하도록 수정했습니다. API 명세에 맞게 파라미터 타입을 정확히 변환하도록 수정했습니다.
- **웹소켓 안정성 강화**: 비정상적인 `ping` 메시지로 인해 발생하던 `JSON PARSING ERROR`를 해결하고, 구독 실패 시 원인을 파악할 수 있도록 에러 로깅을 강화했습니다.
- **전반적인 리팩토링**: 다수의 `ImportError`, `NameError`, `SyntaxError` 등을 해결하는 과정에서 여러 모듈의 의존성 관계를 명확히 하고, 인스턴스 전달 방식을 개선했습니다.

### 주요 파일 및 역할

- **`main_integrated.py`**: 시스템 전체를 초기화하고 실행하는 메인 파일입니다.
- **`core/integrated_trading_system.py`**: 매수/매도/모니터링 워커를 생성하고 관리하는 핵심 오케스트레이터입니다.
- **`web_socket/web_socket_manager.py`**: KIS 실시간 웹소켓 연결 및 데이터 수신을 담당합니다.
- **`web_socket/market_cache.py`**: 수신된 실시간 데이터를 저장하고 조회하는 인메모리 캐시입니다.
- **`api/account_manager.py`**: KIS REST API를 통해 잔고 조회, 주문 실행 등 계좌 관련 기능을 담당합니다.
- **`utils/balance_manager.py`**: 파일(`config/balance.json`)을 통해 잔고를 관리하여 불필요한 API 호출을 줄입니다.

### 검토 및 삭제 대상 파일

- **`main.py`**: `main_integrated.py`가 현재 메인 실행 파일로 보이며, `main.py`는 이전 버전이거나 다른 목적의 파일일 수 있으므로 역할 확인 후 정리가 필요합니다.
- **`test_single_buy.py`**: 이번 디버깅을 위해 생성된 테스트 스크립트로, 향후 유사 문제 발생 시 참고용으로 유지하거나 삭제할 수 있습니다.
- **`trade/` 및 `strategies/` 하위 파일 다수**: 이번 디버깅 과정에서 `market_cache` 인스턴스를 전달받도록 구조가 많이 변경되었습니다. 아직 `None`으로 초기화된 채 방치된 인스턴스가 있을 수 있으므로, 전체적인 테스트와 리팩토링을 통해 의존성 주입을 명확히 할 필요가 있습니다.
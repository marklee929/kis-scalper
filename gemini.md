## 📈 Pyramiding (분할 매수·추가 진입 전략)

### 개요
- 초기 진입 후 **추세가 확인될 때만** 추가 진입하여 수익을 극대화하는 전략.
- "승리한 말에만 베팅한다"는 개념으로, 실패 가능성이 낮아진 시점에 비중을 늘린다.
- 한국 시장 특유의 **초기 급등 → 급락 패턴** 때문에, 적용 시 매우 보수적 조건을 요구한다.

---

### 적용 조건
1. **시간대 제한**
   - 홀딩 하는 종목은 조건에 따라 매매 허용.

2. **가격 조건**
   - 초기 진입가 대비 **+2% 이상 상승** 시점.
   - 당일 고가 대비 이격 **< +5%** (과열 방지).

3. **유동성 조건**
   - 호가 스프레드 ≤ 0.4%.
   - 매수 잔량 비율 ≥ 58%.

4. **거래량/추세 조건**
   - 최근 1분봉 거래량 ≥ 직전 3봉 평균 * 1.5배.
   - VWAP 상단 이격 ≤ 1.2%.
   - **눌림-재돌파 패턴** 확인:
     - +2% 상승 → -0.6%~-1.2% 눌림 → 고점 재돌파 시.

---

### 비중/리스크 관리
- 추가 매수는 **초기 수량의 50%** 한 번만.
- 하루/종목당 최대 1회.
- 추가 매수 체결 후:
  - 합산 평단가 대비 **-0.8% 손절** or 최근 HL(Higher Low) 이탈 시 전량 청산.
  - +1.2% 이상 이익 발생 시, 평단을 BE+수수료 이상으로 끌어올려 **트레일링 시작**.

---

### 장점
- 추세 확인 후 진입 → 승률 향상.
- 수익 극대화 가능.
- 초기 포지션 실패 리스크 분산.

### 단점
- 평균 단가 상승 → 급락 시 손실 확대 가능.
- 스캘핑 특성상 “빠른 매도”와 충돌할 수 있음.
- 한국 장의 급등-급락 패턴에 취약 → 반드시 보수적 적용 필요.

---

### 구현 메모
- `tactics/entry_filters.py`에 `should_pyramid_add()` 함수 추가.
- `core/integrated_trading_system.py`의 매매 루프에 **추가 진입 체크 지점** 삽입.
- **조건 불충족 시 무조건 skip**, 조건 충족 시 1회 한정 체결 후 risk guard 적용.

2025-09-07

## 📈 Pyramiding (분할 매수·추가 진입 전략)

### 개요
- 초기 진입 후 **추세가 확인될 때만** 추가 진입하여 수익을 극대화하는 전략.
- "승리한 말에만 베팅한다"는 개념으로, 실패 가능성이 낮아진 시점에 비중을 늘린다.
- 한국 시장 특유의 **초기 급등 → 급락 패턴** 때문에, 적용 시 매우 보수적 조건을 요구한다.

---

### 적용 조건
1. **시간대 제한**
   - 홀딩 하는 종목은 조건에 따라 매매 허용.

2. **가격 조건**
   - 초기 진입가 대비 **+2% 이상 상승** 시점.
   - 당일 고가 대비 이격 **< +5%** (과열 방지).

3. **유동성 조건**
   - 호가 스프레드 ≤ 0.4%.
   - 매수 잔량 비율 ≥ 58%.

4. **거래량/추세 조건**
   - 최근 1분봉 거래량 ≥ 직전 3봉 평균 * 1.5배.
   - VWAP 상단 이격 ≤ 1.2%.
   - **눌림-재돌파 패턴** 확인:
     - +2% 상승 → -0.6%~-1.2% 눌림 → 고점 재돌파 시.

---

### 비중/리스크 관리
- 추가 매수는 **초기 수량의 50%** 한 번만.
- 하루/종목당 최대 1회.
- 추가 매수 체결 후:
  - 합산 평단가 대비 **-0.8% 손절** or 최근 HL(Higher Low) 이탈 시 전량 청산.
  - +1.2% 이상 이익 발생 시, 평단을 BE+수수료 이상으로 끌어올려 **트레일링 시작**.

---

### 장점
- 추세 확인 후 진입 → 승률 향상.
- 수익 극대화 가능.
- 초기 포지션 실패 리스크 분산.

### 단점
- 평균 단가 상승 → 급락 시 손실 확대 가능.
- 스캘핑 특성상 “빠른 매도”와 충돌할 수 있음.
- 한국 장의 급등-급락 패턴에 취약 → 반드시 보수적 적용 필요.

---

### 구현 메모
- `tactics/entry_filters.py`에 `should_pyramid_add()` 함수 추가.
- `core/integrated_trading_system.py`의 매매 루프에 **추가 진입 체크 지점** 삽입.
- **조건 불충족 시 무조건 skip**, 조건 충족 시 1회 한정 체결 후 risk guard 적용.

---

## Appendix — KIS‑SCALPER Hardening & Upgrade Plan (2025-09-07)

> 목적: 15거래일 집중 테스트 기간 동안 **안정성·재현성·운영 효율**을 극대화하고, 불필요 모듈을 정리하여 러닝코스트를 낮춘다.

### TL;DR — 빠른 개선 5개 (우선 적용)
1) **MarketCache 캔들 보존 확대**: interval별 `deque(maxlen=interval)`을 **거래일 커버(예: 480)** 로 확대. ATR/모멘텀/스크리너 신뢰도↑. fileciteturn6file9  
2) **시작 잔고 정확화**: `trade_summary.set_starting_balance(**총자산**)`(현금+보유평가)로 세팅. 일일 성과 왜곡 제거. fileciteturn3file2  
3) **알림 경로 일원화**: `utils/notifier.py`로 통일, `utils/telegram.py`·`telegram_bot.py`는 레거시로 분리. 이스케이프/MarkdownV2 기준 통일. fileciteturn6file2turn6file4turn6file1  
4) **의존성 정합성**: `utils/code_loader.py`의 **pykrx** 의존을 `requirements.txt`에 명시. fileciteturn6file18  
5) **거래량 필드 일관화**: 틱→캔들/모멘텀 계열에서 `exec_vol` 또는 **누적증분** 사용으로 표준화. 현재 `get_recent_series`는 `acc_vol` 그대로 사용. fileciteturn6file6

---

### 1) 현재 런타임 경로 요약 (정상 작동 라인)
- **본체**: `core/integrated_trading_system.py` — 스크리너/매도판단/모니터링/웨이브 워커 구동. fileciteturn6file15  
- **스크리너**: `strategies/stock_screener.scalping_stock_filter()` — 유동성/변동성/스프레드/모멘텀 점수화 → 상위 30개 선별. fileciteturn6file8  
- **마켓캐시**: `web_socket/market_cache.py` — 틱/캔들/보유스냅샷/트렌드 관리, 체결량 `exec_vol`로 캔들 누적. fileciteturn6file6  
- **알림**: `utils/notifier.py` — 텔레그램 싱글턴, MarkdownV2/이스케이프 처리. fileciteturn6file2  
- **로그/요약**: `analytics/trade_summary.py` — 체결 기록·종료 요약. (초기 시작잔고 세팅 필요) fileciteturn3file2  
- **데이터 로깅**: `data/data_logger.py`, `data/event_logger.py` — 1분봉/이벤트 기록(WS 루프에서 호출). fileciteturn6file0

> 주의: **WebSocket 프로토콜은 `ws://` 유지**(KIS 문서 스펙). 보안 채널(`wss://`) 강제 변경 금지.

---

### 2) 정리 대상(레거시) — 안전 분리
- **auth/**: `token_manager.py`, `token_refresher.py` — 현재는 `api/kis_api`가 토큰·승인키 관리. 레거시.  
- **tactics/**: `*_filters.py`, `*_watcher.py` 전부 — 통합 워커와 중복/미사용. (스파이크/우상향 등 옛 파이프라인) fileciteturn6file12  
- **trade/**: `advanced_position_manager.py`, `buy_engine.py`, `order_executor.py`, `portfolio_optimizer.py`, `position_sizer.py`, `signal_bus.py` — 현 루프 미사용/스텁. fileciteturn6file16  
- **utils/**: `telegram.py`, `telegram_bot.py`, `system_check.py` — 알림/체크 경로 중복·미연동. fileciteturn6file4turn6file1

> 제안: `/legacy` 폴더 신설 후 위 파일 전부 이동. README에 “현 실행경로 미사용” 명시.

---

### 3) 핵심 안정화 패치 (코드 스케치)

**A. MarketCache 캔들 보존 확대 + per‑code 통계 추가**
```diff
# web_socket/market_cache.py
- self._candles[code] = { interval: deque(maxlen=interval) for interval in self._candle_intervals }
+ MAXLEN = self.config.get('cache', {}).get('max_candles_per_interval', 480)
+ self._candles[code] = { interval: deque(maxlen=MAXLEN) for interval in self._candle_intervals }

+ def get_code_stats(self, code: str) -> dict:
+     """최근 1/3/5/10분봉 기반 변동성·모멘텀 등 간단 통계"""
+     out = {}
+     for iv in [1,3,5,10]:
+         c = list(self.get_candles(code, iv))
+         if len(c) >= 16:
+             closes = [x['close'] for x in c[-16:]]
+             out[f'mom_{iv}m'] = (closes[-1]-closes[0])/max(closes[0],1e-6)*100
+     return out
``` 
근거: 현재 interval별 `maxlen=interval`로 매우 짧아(1분봉=1) 지표 정확도 저하. `exec_vol`로 캔들 누적 중. fileciteturn6file9turn6file6

**B. 최근 시계열 볼륨 표준화**
```diff
- vol.append(item['acc_vol'])
+ vol.append(item.get('exec_vol', 0.0))  # 체결량(혹은 acc_vol 증분)
```
근거: 단기 스파이크/모멘텀 탐지엔 **누적량(acc_vol) 대신 체결량**(또는 누적증분)이 적합. fileciteturn6file6

**C. 시작 잔고 = 총자산으로 세팅**
```diff
# core/integrated_trading_system.py (초기화 직후)
- trade_summary.set_starting_balance(cash_balance)
+ trade_summary.set_starting_balance(self.beginning_total_assets)  # 현금+보유평가
```
근거: trade_summary가 시작/종료 잔고로 일일 성과 산출. 현금만 세팅 시 왜곡. fileciteturn3file2

**D. 알림 경로 통일**
```diff
- from utils.telegram import send_telegram_message, send_telegram_summary_if_needed
+ from utils.notifier import notifier
# 사용처:
- send_telegram_message(msg)
+ notifier.send_message(msg)
```
근거: logger의 TODO가 `telegram` 유틸과 충돌 경고. `notifier`는 MarkdownV2/이스케이프 포함. fileciteturn6file12turn6file2

**E. requirements 정합성 (`pykrx`)**
- `utils/code_loader.py`가 `pykrx` `stock.get_market_ohlcv/…` 사용 → `requirements.txt`에 `pykrx` 명시. fileciteturn6file18

---

### 4) 리스크/리워드 파라미터 표준 (현재 값 기준)
- **개별 포지션 청산**: 손절 −2%, ATR×2 컷, 추적손절(진입 후 +1% 이상 활성, DD 임계 동적), 모멘텀 하락, 횡보/시간만료(>600s·>1800s). fileciteturn6file14  
- **포트폴리오 가드**: (통합 워커 내부 규칙 유지 / `risk_management.py`와 충돌 없도록 주석화).

> 파라미터는 `Config`로 드라이브하고, 테스트 기간엔 **고정**해 재현성 확보.

---

### 5) 관측·리포팅(Observability)
- **실시간 성능 트래커 연동**: `_monitoring_worker()` 루프에서 총자산·일 PnL·승률·낙폭·포지션수를 `performance_tracker.record_metrics(...)`로 기록 → 일일 리포트 저장. fileciteturn3file1  
- **체결 기록**: `trade_summary.record_trade()`는 유지, 종료 시 `print_shutdown_summary()`로 요약·저장. 시작잔고 정확화 필수. fileciteturn3file2  
- **텔레그램**: 모든 알림은 `utils/notifier.notifier.send_message()`로 단일화. fileciteturn6file2

---

### 6) 운영 런북(15거래일 테스트 기준)
1. **월요일(현금화/세팅)**: 실험 전용 계좌 1,000 세팅, 레거시 모듈 비활성.  
2. **매일 개장 전**: `run_trading_system.bat` 실행 → WS 연결·초기 구독·스크리너 정상 확인(로그).  
3. **장중**:  
   - 신규 구독: 거래량 상위 → 스크리너 필터 → 구독 관리(상한 `max_subscriptions`). fileciteturn6file15  
   - 매도판단: 손절/ATR/트레일/모멘텀/시간만료. fileciteturn6file14  
   - 웨이브(보조): 기본 전략 포지션 없는 종목만 적용(필요 시 시장가 옵션). fileciteturn6file15  
4. **장마감**: `trade_summary` 저장/전송, 로그 압축, 데이터 백업(1분봉/이벤트).  
5. **주 단위**: 백테스트 엔진으로 1분봉 로그 점검, 규칙 이탈 여부 확인. fileciteturn3file0

---

### 7) 디렉토리 정리안 (운영 vs 레거시)

```
kis-scalper/
  core/                     # (운영) config, integrated_trading_system, position_manager
  api/                      # (운영) kis_api, account_manager
  web_socket/               # (운영) web_socket_manager, market_cache
  strategies/               # (운영) stock_screener, wave_scalper
  analytics/                # (운영) trade_summary, performance_tracker, backtesting_engine
  utils/                    # (운영) notifier, logger, code_loader, balance_manager, safe_request
  data/                     # (운영) data_logger, event_logger
  legacy/                   # (레거시) auth/token_*, tactics/*, trade/*, utils/{telegram,telegram_bot,system_check}, main.py 등
```

---

### 8) 15거래일 검증 목표/지표
- **성공기준**:  
  - 기대값(μ) > 0: 승률×익절% − (1−승률)×손절% > 0  
  - 일일 손익률 표준편차 ↓, 연속 5일 누적 +  
  - 규칙 위반(손절/오버트레이딩/추적손절 미적용) 0회
- **기록**: 진입·청산 시각/사유, PnL%, 체결정보, 트레일링 on/off, 모멘텀·ATR 값 스냅샷.

---

### 9) Backtest to Prod — 교량
- `backtesting_engine.py` 엔트리 신호를 실제 스캘핑 규칙으로 치환(모멘텀/체결량 스파이크/스프레드). 리포트 시작 시각 `None` 가드. fileciteturn3file0  
- 실전 로그(1분봉) → 백테스트 재현 → 규칙 이탈 감지 체계화.

---

### 10) 오픈 이슈 / 추후 과제
- 포트폴리오 가드(‑3%, +5%, +3% trail)와 `risk_management.py` 규칙 일원화.  
- 웨이브 스캘퍼 체결 안정화(시장가 옵션 플래그) 및 `volume` 키를 `exec_vol` 또는 누적증분으로 표준화.  
- `config` 기본 ENV를 DEMO로 전환, `secrets.json` 미존재 시 실행중단 플래그.

---

> NOTE: **KIS WebSocket은 `ws://` 스펙 고정** — 보안 채널 강제 변경 금지(장애 유발 위험). 운영망 정책은 KIS 문서에 따름.

## 📈 Pyramiding (분할 매수·추가 진입 전략)

### 개요
- 초기 진입 후 **추세가 확인될 때만** 추가 진입하여 수익을 극대화하는 전략.
- "승리한 말에만 베팅한다"는 개념으로, 실패 가능성이 낮아진 시점에 비중을 늘린다.
- 한국 시장 특유의 **초기 급등 → 급락 패턴** 때문에, 적용 시 매우 보수적 조건을 요구한다.

---

### 적용 조건
1. **시간대 제한**
   - 홀딩 하는 종목은 조건에 따라 매매 허용.

2. **가격 조건**
   - 초기 진입가 대비 **+2% 이상 상승** 시점.
   - 당일 고가 대비 이격 **< +5%** (과열 방지).

3. **유동성 조건**
   - 호가 스프레드 ≤ 0.4%.
   - 매수 잔량 비율 ≥ 58%.

4. **거래량/추세 조건**
   - 최근 1분봉 거래량 ≥ 직전 3봉 평균 * 1.5배.
   - VWAP 상단 이격 ≤ 1.2%.
   - **눌림-재돌파 패턴** 확인:
     - +2% 상승 → -0.6%~-1.2% 눌림 → 고점 재돌파 시.

---

### 비중/리스크 관리
- 추가 매수는 **초기 수량의 50%** 한 번만.
- 하루/종목당 최대 1회.
- 추가 매수 체결 후:
  - 합산 평단가 대비 **-0.8% 손절** or 최근 HL(Higher Low) 이탈 시 전량 청산.
  - +1.2% 이상 이익 발생 시, 평단을 BE+수수료 이상으로 끌어올려 **트레일링 시작**.

---

### 장점
- 추세 확인 후 진입 → 승률 향상.
- 수익 극대화 가능.
- 초기 포지션 실패 리스크 분산.

### 단점
- 평균 단가 상승 → 급락 시 손실 확대 가능.
- 스캘핑 특성상 “빠른 매도”와 충돌할 수 있음.
- 한국 장의 급등-급락 패턴에 취약 → 반드시 보수적 적용 필요.

---

### 구현 메모
- `tactics/entry_filters.py`에 `should_pyramid_add()` 함수 추가.
- `core/integrated_trading_system.py`의 매매 루프에 **추가 진입 체크 지점** 삽입.
- **조건 불충족 시 무조건 skip**, 조건 충족 시 1회 한정 체결 후 risk guard 적용.

// 2025-09-11

아래 명세로 한국 주식 자동매매 코드를 작성/리팩터링해줘. 
기존 모듈명 예시는 유지해도 되고, 새로운 파일로 나눠도 된다.

========================
[전략 개요]
- 장중(09:30~15:20)엔 매수 없음. 스코어만 실시간 업데이트.
- 15:20~15:30 종가에 상위 5종목을 시장가 매수(현금 100% = 5등분).
- 다음날 09:00~09:30에 보유 전 종목을 실시간 모니터링하며 트레일링 매도.
- 09:30 정각: 미매도 잔량 전량 시장가 청산(손익무관).

========================
[데이터/모듈 요구]
1) WebSocket 실시간 시세 (틱/체결강도/호가): subscribe/unsubscribe 지원
2) 계좌/잔고 API: 보유종목 최대 30개 조회
3) 주문 API: 시장가 매수/매도
4) 로거/리포트: 체결·익절·손절·강제청산 이벤트 기록

========================
[스코어링 파이프라인]
- 대상군 생성: 거래대금 상위 100 → 점수화 → 상위 30 유지
- 점수 구성요소(가중합, 표준화 후 0~100 스케일):
  S = 0.35*V + 0.25*K + 0.20*R + 0.10*C + 0.10*L
  - V(거래량 유지율): sum(vol 14:50~15:20) / sum(vol 13:00~14:00)
  - K(체결강도 평균): 14:50~15:20 평균 체결강도
  - R(변동성 품질): 표준편차/ATR 대비 상승 편향(상승 캔들 비율, 고가근접도)
  - C(클로징 스트렝스): (종가-저가)/(고가-저가) with 분모 0 방지
  - L(막판 대금 증가율): 거래대금(14:50~15:20) / 거래대금(14:20~14:50)
- 제외필터: ETF/ETN 키워드(“KODEX, TIGER, ARIRANG, HANARO, KBSTAR, KOSEF”), 관리·투자경고·단일가/VI 중인 종목
- 랭킹은 매 분 갱신, 15:20에 최종 랭킹 스냅샷 사용

========================
[종가 매수 로직]
- 트리거: 15:20:00
- 상위 5종목 선정(동점 시 거래대금 큰 순)
- 포지션 사이징: 현금의 20%씩 5종 균등. (미체결/잔여현금은 버퍼로 남겨도 OK)
- 주문: 시장가 매수(종가체결 영역)

========================
[다음날 매도 로직(09:00~09:30)]
- 대상: 전일 종가 매수 종목 + 기존 보유 잔량(최대 30)
- 1분봉 기준 피크 추적 트레일링:
  - peak = max(peak, 현재가)
  - profit = (현재가/평단 - 1)
  - 조건:
    (A) profit >= MIN_PROFIT_PCT 이고 (peak/현재가 - 1) >= TRAIL_DROP_PCT → 즉시 시장가 매도
    (B) profit < MIN_PROFIT_PCT 이더라도, (현재가 < 시초가 * OPEN_FAIL_DROP) → 즉시 시장가 매도
- 반등 시도는 무시, 신속 청산 우선.
- 09:30:00 강제청산: 남은 전량 시장가 매도.

========================
[오픈 갭 리스크 완화(선택적)]
- 08:30~09:00 예상체결가/호가로 갭 위험 사전 표기:
  - 예상 -3% 이상이면 “오픈 리스크”로 표시해두고 시초 매도 조건(B)에 자동 해당.

========================
[파라미터 (config)]
MARKET_OPEN        = 09:00
MARKET_CLOSE       = 15:30
BUY_START          = 15:20
OPEN_EXIT_END      = 09:30
TOPK_BUY           = 5
EACH_BUY_PCT       = 0.20      # 5종 균등
TRAIL_DROP_PCT     = 0.006     # 0.6% 하락 시 트레일링 발동
MIN_PROFIT_PCT     = 0.002     # +0.2% 이상 이익일 때만 트레일링 유효
OPEN_FAIL_DROP     = 0.985     # 시초가 대비 -1.5% 하락 시 즉시 손절
MIN_TURNOVER       = 10_000_000_000  # 100억 이상만
EXCLUDE_KEYWORDS   = ["KODEX","TIGER","ARIRANG","HANARO","KBSTAR","KOSEF"]

========================
[엣지 케이스/안전장치]
- 거래정지/VI/단일가 감지 시: 해당 종목 즉시 제외, 보유 중이면 09:30 강제청산 로직에만 걸림
- 주문 실패/부분체결: 잔량은 09:30 강제청산 규칙 동일 적용
- 데이터 결손: 최근값 carry-forward, 결측 비율>20%면 스코어 계산 제외
- 중복 매수 금지: 당일 종가 매수는 1티커 1회 제한
- 로그: (시간, 코드, 액션, 수량, 가격, PnL, 규칙트리거) 필수 기록

========================
[함수/파일 설계 예시]
- strategies/score_monitor.py
  - update_universe(), compute_scores(), topN(n=30), snapshot_at(time=15:20)
- execution/close_buy.py
  - select_top5_and_buy(snapshot), size_positions(cash), market_buy_batch(list)
- execution/open_sell.py
  - track_peak_and_trail(ws_stream), should_sell(state), market_sell(code, qty)
  - force_liquidate_all(at=09:30)
- risk/filters.py
  - exclude_keywords(), exclude_special_remarks(), min_turnover_filter()
- infra/websocket_runner.py
  - subscribe(codes), on_tick(cb), on_minute_close(cb)
- reporting/trade_summary.py
  - write_event(), daily_summary()

테스트:
- 가짜 틱 데이터로 09:00~09:30 트레일링 동작 시뮬레이션
- 15:20 스냅샷 고정 후 5종 매수 배분 검증
- 주문 실패/부분체결/VI 전환 시 흐름 점검(예외처리)

-- 종가 검증 추가
목적

한국 주식 종가매매 자동화 시스템을 구현한다.
장중에는 후보 스코어만 업데이트하고, 15:20~종가에 상위 5종목을 시장가 매수, 다음날 09:00~09:30 트레일링 매도 후 09:30 강제청산한다. 주문은 전부 시장가로 처리한다.

운영 타임라인(Asia/Seoul)

장중 스코어링: 09:30 ~ 15:20 (매수 없음, 점수만 갱신)

종가 매수: 15:20 트리거 → 종가(15:30) 체결 영역에서 Top5 균등 매수

다음날 매도: 09:00 ~ 09:30

1분봉 기준 피크 추적(trailing)으로 최대한 높은 가격에서 즉시 매도

하락 전환 시 반등 무시, 즉시 시장가 청산

09:30 정각: 잔량 전량 강제 시장가 청산

데이터/의존

WebSocket: 실시간 틱/1분봉, 체결가/체결강도, 호가(스프레드·호가잔량)

계좌/잔고 API: 보유 종목(최대 30개)·평단·수량 조회

주문 API: 시장가 매수/매도

지수/섹터 데이터: KOSPI/KOSDAQ 지수, 섹터 지수(또는 섹터 대표 ETF)

유니버스 & 제외 규칙

장중 거래대금 상위 100종목 → 점수화 → 상위 30 유지(rolling)

제외: ETF/ETN 키워드(“KODEX, TIGER, ARIRANG, HANARO, KBSTAR, KOSEF”), 관리/투자경고, 거래정지, VI/단일가

최소 유동성: 당일 거래대금 ≥ 100억(파라미터화)

스코어링 지표(합본)
A. 기존(제미나이 제안 3개)

종가 모멘텀(Closing Price Momentum)

정의: 장 마감 근접 구간(예: 15:00~15:20) 현재가의 고가 근접도

효과: 끝까지 힘이 유지되는 종목 선호

이동평균선 정배열(MA Alignment)

정의: 1분봉 기준 5 > 20(>60) 정배열 여부 및 거리

효과: 일시 급등이 아닌 지속 상승 추세 선별

시장대비 상대강도(Relative Strength vs Market, RS_mkt)

정의: (14:50~15:20) 종목 수익률 − 지수 수익률

효과: 시장보다 더 강한 종목 선별

B. 보강(추가 6개)

클로징 드라이브(Closing Drive, CD)

정의: 15:00→15:20 가격 기울기 / 당일 ATR (정규화)

효과: 막판 “끌어올림”이 의미 있는 추세 가속인지 측정

VWAP 프리미엄(PVWAP)

정의: (Close - VWAP) / VWAP (15:20 스냅샷)

효과: 종가가 VWAP 위면 다음날 연속성↑

마감 집중 거래비율(Last-30min Volume %, V30)

정의: Vol(15:00~15:30) / Vol(전일 장중)

효과: 막판 수급 집중 확인

레인지 확장 품질(Range Expansion Quality, REQ)

정의: (일중 True Range / ATR_20d) × (상승 캔들 비율·고가근접도 가중)

효과: 단순 흔들기 vs 의미 있는 확장 구분

유동성 패널티(Liquidity Penalty, LP) (감점 항목)

정의: LP = α*(스프레드%) + β*(1/최상위 N틱 호가잔량합)

효과: 체결 미끄럼(슬리피지) 리스크 축소

섹터 상대강도(Relative Strength vs Sector, RS_sector)

정의: (14:50~15:20) 종목 수익률 − 섹터 수익률

효과: 섹터 내 주도주 선별

참고: 고가근접도 CR = (Close - Low) / (High - Low + ε), ε로 0-division 방지.
VWAP은 장중 누적 Σ(price×vol)/Σ(vol).

점수식(정규화 후 가중합, 예시)

각 지표는 z-score → 0~100 스케일로 정규화. 상관 높은 지표는 중복 반영 최소화.

S_total = 
  0.20*CD          # 클로징 드라이브
+ 0.15*PVWAP       # VWAP 프리미엄
+ 0.20*V30         # 마감 집중 거래비율
+ 0.15*REQ         # 레인지 확장 품질
+ 0.15*RS_mkt      # 시장대비 상대강도(기존)
+ 0.10*RS_sector   # 섹터대비 상대강도(신규)
+ 0.05*MA_align    # 정배열(5>20>60)
- 0.10*LP          # 유동성 패널티(감점)


임계 컷(점수 계산 전):

거래대금 < MIN_TURNOVER(기본 100억) 제외

스프레드 > MAX_SPREAD_PCT(예: 0.15%) 제외

15:18~15:20 -0.8% 이상 급락: 제외

당일 +15% 이상 & V30 > 35%: 과열 감점 또는 제외

종가 매수 로직

트리거: 15:20:00에 스코어 스냅샷 고정 → 정렬

선정: 상위 5종목(동점 시 거래대금 큰 순)

배분: 가용 현금 20% × 5 균등

주문: 시장가 매수(종가 체결 영역)

다음날 매도 로직(09:00~09:30)

대상: 전일 종가 매수 종목 + 기존 보유 전체(최대 30개)

피크 추적 트레일링(1분봉)

peak = max(peak, price_now)

profit = (price_now / avg_cost - 1)

조건:

(A) profit ≥ MIN_PROFIT_PCT AND (peak/price_now - 1) ≥ TRAIL_DROP_PCT ⇒ 즉시 시장가 매도

(B) profit < MIN_PROFIT_PCT AND (price_now < open_price * OPEN_FAIL_DROP) ⇒ 즉시 시장가 손절

반등(v-rebound) 은 고려하지 않음(즉시 청산 우선)

09:30:00: 잔량 전부 시장가 강제청산

(옵션) 08:30~09:00 예상체결가로 갭 하락 -3% 이상이면 자동으로 (B) 조건 해당.

주문 정책

모든 매수/매도 = 시장가

중복매수 금지: 하루 한 티커 1회

부분체결/실패 발생 시 남은 잔량은 09:30 강제청산 규칙 그대로 적용

파라미터 (config 예시)
MARKET_OPEN        = "09:00"
MARKET_CLOSE       = "15:30"
BUY_START          = "15:20"
OPEN_EXIT_END      = "09:30"

TOPK_BUY           = 5
EACH_BUY_PCT       = 0.20          # 5종 균등
MIN_TURNOVER       = 10_000_000_000 # 100억
MAX_SPREAD_PCT     = 0.0015        # 0.15%

TRAIL_DROP_PCT     = 0.006         # 0.6% 하락 시 트레일링 발동
MIN_PROFIT_PCT     = 0.002         # +0.2% 이상 수익부터 트레일링 유효
OPEN_FAIL_DROP     = 0.985         # 시초가 대비 -1.5% 손절

EXCLUDE_KEYWORDS   = ["KODEX","TIGER","ARIRANG","HANARO","KBSTAR","KOSEF"]

모듈/함수 구조(예시 이름, 자유 변경)

strategies/score_monitor.py

update_universe() : 거래대금 상위 100 추출

compute_scores() : 지표 계산 → 정규화 → S_total 산출

topN(n=30) : 상위 30 유지

snapshot_at("15:20") : 최종 랭킹 고정

execution/close_buy.py

select_top5(snapshot)

size_positions(cash, n=5, pct=0.20)

market_buy_batch(tickers, sizes)

execution/open_sell.py

subscribe_positions(ws, holdings≤30)

track_peak_and_trail(tick) → (A)/(B) 판단

market_sell(code, qty)

force_liquidate_all("09:30")

risk/filters.py

apply_exclusions(df, keywords, min_turnover, max_spread)

cut_late_dip(df, window=2min, thr=-0.8%)

infra/websocket_runner.py

subscribe(codes) / unsubscribe(codes)

on_tick(cb), on_minute_close(cb)

reporting/trade_summary.py

이벤트 로그: (시간, 코드, 액션, 수량, 가격, PnL, 트리거 규칙)

일일 요약 리포트

로깅 & 리포트

필수 로그: 주문 전/후, 체결, (A)/(B)/강제청산 트리거, 스코어 스냅샷 Top30/Top5

일일 리포트: 종가매수 목록, 익일 청산 결과, 총손익, 슬리피지·체결율

테스트/검증(요구)

백테스트(필수): 최근 60거래일, 동일 파라미터로 Top5 종가 매수/오픈 30분 청산 시뮬레이션

아블레이션:

(i) 기본 3지표만

(ii) + PVWAP·V30·CD

(iii) + RS_sector·LP

(iv) + REQ
→ 각 단계별 누적 수익률/최대 낙폭/승률/체결율 비교

슬리피지 테스트: 스프레드·Depth 기반 체결가 오차 시뮬레이션

실시간 모의: 틱 재생으로 09:00~09:30 트레일링 로직 작동 검증

산출물

파이썬 모듈 일체 + 설정 파일(config_trade_windows.py)

실행 엔트리(main.py):

09:30~15:20 스코어 업데이트 루프

15:20 종가매수 실행

(다음날) 09:00~09:30 트레일링 매도 + 09:30 강제청산

README: 환경변수, API 키, 실행 방법, 파라미터 설명, 백테스트 방법

구현 메모(수식 힌트)

CD: 15:0015:20 1분봉 종가 선형회귀 기울기 / ATR_day, z→0100

PVWAP: 장중 누적 VWAP, 15:20 스냅샷 사용

V30: vol_last30 / vol_total

REQ: TR_day/ATR_20d * (up_candle_ratio^γ) * (CR^δ) (γ, δ는 0.3~0.4 가중)

LP: α*spread_pct + β*(1/depth_topN) → 점수는 100−정규화

정규화: 롤링 분포(z-score) → [0,100], 이상치 clip
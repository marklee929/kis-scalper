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

2025-09-16
# 📌 종가매매 개선안 (Top5 균등매수 → 점수가중·품질필터·리스크가드)

## TL;DR

* **Top5 균등매수 폐기** → **점수가중 비중배분**(softmax) + **품질필터 3종**(Closing Drive·VWAP 프리미엄·마지막 30분 거래량 비중).
* **종가 근접 급락 회피**: 15:00\~15:20 기울기(Closing Drive)·하락턴 컷, 스프레드/유동성 패널티 적용.
* **리스크가드 일원화**: 시가 실패컷, 최소이익 트레일, 09:30 강제정리 유지.

---

## 1) 문제 정의

* 장 마감 직전 Top5 균등매수는 **스코어 편차**·**유동성 위험**·**종가 급락 전환**을 반영하지 못함.
* 결과: 손실 종목 비중이 과대(5개 중 3- 손실), 플러스 종목 이익이 평균화되어 희석.

## 2) 성공 기준

* 15거래일 백테스트/시뮬 결과 **익일 09:30 기준 총합 PnL↑, MDD↓, 승률↑**.
* 체결 실패/부분체결/VI 전환 등 **운영 이슈 로그**가 정상 기록되고, 복구 로직 동작 확인.

---

## 3) 스코어링 강화 (추가/보강 지표)

### 3.1 Closing Drive (CD)

* 구간: **15:00\~15:20 1분봉 종가**.
* 계산: `slope = polyfit(x, prices, 1) / avg_price` 표준화 → `cd = clip((slope/dailyATR)*50 + 50, 0, 100)`.
* 효과: **마감까지 힘 유지 종목 선호**, 종가 직전 하락 전환 종목 배제.

### 3.2 VWAP 프리미엄 (PVAP)

* `pvap = 50 + premium(%) * 25` (1%↑마다 +25점, 0\~100 clip).
* 효과: **종가가 VWAP 상단**에 있는 흐름 우선.

### 3.3 마지막 30분 거래량 비중 (V30)

* `pct = last30mVol / totalVol`; `v30 = 25 + pct*2.5` (10%→50점, 30%→100점).
* 효과: **마감 자금 유입 확인**.

### 3.4 MA 정배열, REQ, RS(시장/섹터) 기본 유지

* 최소 세트: **MA(5>20>60), REQ(당일 TR/20D ATR, 캔들 우상향·CR 반영), RS\_mkt/RS\_sector**.

### 3.5 유동성 패널티 (LP)

* 호가 스프레드 기반: `lp = clip((spreadPct - 0.1%)*250, 0, 100)`.
* **총점에서 −0.1×LP** 가중.

### 3.6 종합 점수식 (가중)

```
score = 0.20*CD + 0.15*PVAP + 0.20*V30 + 0.15*REQ + 0.15*RS_mkt + 0.10*RS_sector + 0.05*MA - 0.10*LP
score ∈ [0, 100]
```

---

## 4) 후보 필터 (하드컷)

* **거래대금 ≥ 10억** (파라미터화: `MIN_TURNOVER`)
* **ETF/ETN 키워드 제외**: "KODEX, TIGER, ARIRANG, HANARO, KBSTAR, KOSEF, 인버스, 레버리지"
* **스프레드 ≤ 0.15%** (파라미터화: `MAX_SPREAD_PCT`)
* (선택) 관리/투자경고/단일가/정지 종목 제외 플래그 연동

---

## 5) 매수 비중 산식 (균등 → 점수가중)

### 5.1 Softmax 가중 (온도 τ)

* TopN(기본 5) 각 `zi = score_i`에 대해

```
w_i = exp(zi/τ) / Σ exp(zj/τ),  τ∈[8,15] (기본 10)
alloc_i = floor((cash_total * w_i) / price_i)  # 주수 단위
```

* 효과: 점수 격차를 **완만하지만 확실하게** 비중에 반영. τ↓이면 공격적.

### 5.2 최소/최대 비중 가드

* `w_min = 0.10`, `w_max = 0.35` 클램핑 후 **재정규화**.

### 5.3 체결 실패 대비

* 15:20\~15:29:30 **시장가 우선**, 실패 시 2회 재시도(250ms 간격). 15:29:30 이후 잔여분 **전량 시장가**.

---

## 6) 매도(익일 09:00\~09:30) 리스크가드

* **트레일링 수익실현**: `min_profit_pct_sell = +0.2%`, `trail_drop_pct_sell = 0.6%`
* **시가 실패컷**: 이익 미달 상태에서 **시가 대비 −1.5% 이탈** 시 즉시 시장가 청산.
* **09:30 강제청산**: 잔량 전부 시장가.

---

## 7) Fallback & 예비후보

* 실시간 후보 <5개일 때: 거래대금 상위 리스트에서 **ETF/ETN 제거** 후 보충(최대 5개 충족).
* Fallback 종목은 `reason: "fallback_volume"` 로깅.

---

## 8) 구현 작업 (파일/함수 포인트)

1. **스코어링 강화**

* `strategies/closing_price_trader.py`

  * `calculate_closing_drive()` / `calculate_vwap_premium()` / `calculate_last_30min_volume_pct()` 보강
  * `calculate_closing_price_score()`에 **LP·REQ·RS 가중** 최종식 확정
  * `apply_all_filters()`에 **스프레드·거래정지/경고 필터** 추가

2. **매수 비중 로직 교체**

* `core/integrated_trading_system.py`

  * `_closing_price_buy_worker()`에서 **균등배분 → softmax 가중**으로 교체
  * 체결 실패/부분체결 **재시도 루틴** 삽입(시장가)

3. **구독/데이터 품질**

* `web_socket/market_cache.py`

  * 1분봉 **VWAP 계산용 누적(가격×체결량)** 유지, `exec_vol` 표준화
  * 스프레드 계산(최우선 매수·매도호가) 제공

4. **리스크가드 일원화**

* `core/integrated_trading_system.py`

  * `_opening_sell_worker()`에 **시가 실패컷**(open\_fail\_drop\_ratio) 재확인
  * 트레일 스탑 파라미터를 `core/config.py`로 이동

5. **로깅/리포팅**

* `analytics/trade_summary.py`:

  * **비중, 체결가, 재시도 횟수, reason tag** 기록
  * 일자별 **PnL·승률·MDD** 요약에 **가중전략 플래그** 추가

---

## 9) 신규/변경 파라미터 (config)

```yaml
trading:
  min_turnover: 1000000000      # 10억
  max_spread_pct: 0.0015        # 0.15%
  top_n_buy: 5
  softmax_tau: 10.0
  weight_min: 0.10
  weight_max: 0.35
  min_profit_pct_sell: 0.002    # +0.2%
  trail_drop_pct_sell: 0.006    # -0.6% from peak
  open_fail_drop_ratio: 0.985   # 시가 대비 -1.5%
```

---

## 10) 의사코드 (매수 파트 교체)

```python
# inside _closing_price_buy_worker()
N = config.trading.top_n_buy
cands = closing_price_candidates[:N]
# 점수 배열
scores = np.array([c['total_score'] for c in cands], dtype=float)
# softmax with temperature tau
z = scores / config.trading.softmax_tau
w = np.exp(z - z.max()); w = w / w.sum()
# clamp
w = np.clip(w, config.trading.weight_min, config.trading.weight_max)
w = w / w.sum()
# 배분 → 수량 산정
for c, wi in zip(cands, w):
    cash_i = total_cash * wi
    qty = int(cash_i // get_price(c['code']))
    place_market_buy(code=c['code'], qty=qty, retry=2)
```

---

## 11) 테스트 시나리오 (필수)

* **리플레이**: 3거래일 틱/1분봉 덤프 재생 → 15:20 스냅샷 고정, 매수 배분·체결 시뮬.
* **엣지**: 후보 3개 이하 / 스프레드 과대 / VI 진입 / 부분체결 / API 오류 재시도.
* **메트릭**: 승률·익일 09:30 PnL·평균 보유시간·체결성공률·슬리피지(시장가)·재시도 수.

---

## 12) 롤백 전략

* `trading.use_weighted_allocation=false` 플래그로 **균등배분** 즉시 복귀.
* 파라미터 별도 프로파일: `profile/eod_weighted.yaml` ↔ `profile/eod_equal.yaml` 스위치.

---

## 13) 운영 체크리스트

* 15:00 이전 **마켓캐시 VWAP·스프레드 정상화** 확인.
* 15:20 트리거 시 텔레그램에 **후보·점수·예비/실시간 구분** 출력.
* 09:00\~09:30 매도 사유 태그: `TrailingStop / OpenFail / Force0930`.

## 매도 수정사항 :: 
그리고 지금 9:00 ~ 9:30 전일 종가 구매한 종목을 모니터링하면서 파는게 안되는거같은데 확인해줄래.. 
ChatGPT의 말:

봤더니 09:00~09:30 매도 모니터링 로직 자체는 이미 구현돼 있어. 핵심은 core/integrated_trading_system.py 안의 _opening_sell_worker 함수야.

현재 동작 구조

시간 조건: _is_sell_time() → 09:00 ≤ now < 09:30

integrated_trading_system

.

시작 시 초기화: 보유 종목(position_manager.positions)을 positions_to_sell로 복사

integrated_trading_system

.

시가/피크 설정: market_cache.get_quote(code)로 시가를 받아 sell_open_prices와 sell_peaks에 기록

integrated_trading_system

.

실시간 확인 루프: 2초마다 현재가를 조회 → _check_sell_conditions() 호출

integrated_trading_system

.

매도 조건 (_check_sell_conditions)

integrated_trading_system

(A) 트레일링 스탑: +0.2% 이상 수익 상태에서 고점 대비 0.6% 이상 하락 시 매도.

(B) 시가 실패컷: 수익 미달 상태 + 시가 대비 -1.5% 하락 시 매도.

09:30 강제청산: 잔여 전량 시장가 매도

integrated_trading_system

.

안 되는 이유 가능성

market_cache.get_quote() 문제
→ 시가/실시간 가격이 캐시에 안 들어오면 open_price나 current_price가 0 → 조건 판정 자체가 스킵됨.

포지션 초기화 안 됨
→ self.positions_to_sell가 비어 있으면 루프가 바로 continue

integrated_trading_system

.

체결/구독 누락
→ 08:58 웹소켓 연결(_wait_and_connect_ws)이 실패하면 시세 업데이트 자체가 안 됨

integrated_trading_system

.

조건 과도 보수적
→ +0.2% 수익을 못 찍으면 (A) 안 걸리고, -1.5% 이상 안 떨어지면 (B)도 안 걸림. 결국 09:30 강제청산만 남음.

즉 “안 팔린다”는 건 로직이 없는 게 아니라 시세 데이터 캐시/구독 문제가 제일 의심이야. 실제 매도조건 두 개도 너무 좁게 잡혀서 대부분 케이스가 09:30으로 밀릴 가능성도 있음.

👉 확인할 포인트:

09:00 직후 market_cache.get_quote(code) 값이 들어오고 있는지 로그 찍기.

positions_to_sell 초기화 시점에 종목이 제대로 들어갔는지 확인.

config.trading.min_profit_pct_sell, trail_drop_pct_sell, open_fail_drop_ratio 값이 의도대로인지 체크.

원하면 내가 로그 찍을 위치랑 조건 완화하는 수정 포인트까지 정리해줄까?

출처
나의 말:
어 수정포인트만 집어줘.. 오늘은 일단 보유하면서 모니터링해야할듯.. 지금 -9%야.. 이러면 손해가 심각하지.. 
ChatGPT의 말:
35s 동안 생각함

오케이. “안 팔리는” 건 로직보단 시가/실시간 시세 캐시, 임계값, 구독 타이밍 문제가 더 유력. 오늘은 홀딩한다 했으니, 내일부터 먹히게 할 최소 수정 포인트만 콕 집어줄게.

반드시 고칠 것 (필수 6개)

시가 세팅 버그(TODO 방치)

파일: core/integrated_trading_system.py → _opening_sell_worker()

수정: 시가를 market_cache.get_quote(code)로 “임시” 세팅 중인 TODO 제거하고, 09:00 첫 틱 기준 시가로 고정 저장.
예) open_price = market_cache.get_open_price(code, date=today) 없으면 09:00~09:00:30 첫 틱을 시가로 픽스. 지금은 quote 미수신 시 0으로 남아 조건이 안 걸릴 수 있음.

보유종목 → 매도대상 이관 시점 확인

파일: 동일

내용: 09:00 진입 시 positions_to_sell = dict(position_manager.positions)가 비어 있으면 바로 종료됨. 장 시작 전에 position_manager가 실제 보유 포지션으로 채워졌는지 로그로 확인/보장.
초기화 경로에서 보유 포지션은 복원되지만(정상) A프리픽스 정규화가 안 맞으면 캐시 조회가 실패함 → 정규화 유지 확인.

웹소켓 08:58 연결/구독 보장

파일: _wait_and_connect_ws() / _update_subscriptions()

내용: 08:58에 WS 연결 실패하면 아침 내내 get_quote()가 빈값. 연결 실패 시 즉시 에러 반환/종료하는 현재 흐름 유지 + 08:59에 보유종목 재구독 한 번 더(owned_codes는 항상 구독 유지 로직 있음).

매도 임계값 현실화(너무 보수적)

파일: _check_sell_conditions() + config

변경 파라미터(익일 아침 전용 권장 시작값):

min_profit_pct_sell: 0.002 → 0.001 (0.1%)

trail_drop_pct_sell: 0.006 → 0.004 (고점대비 -0.4%)

open_fail_drop_ratio: 0.985 → 0.99 (시가대비 -1%면 컷)
이렇게 안 낮추면 대부분 09:30 강제청산으로 밀림.

하드 스탑(평단 기준) 추가 — 조건 (C)

파일: _check_sell_conditions()

내용: 아래 한 줄 추가. 급락(-9%) 방어용 평단 대비 고정 손절:

if current_price <= avg_price * 0.97:
    self._execute_sell(code, "Hard Stop (-3% from avg)")
    return


(퍼센트는 config로 노출 추천: hard_stop_from_avg: 0.97)

09:30 강제청산은 유지하되, ‘오늘만’ 끄고 싶으면

파일: _opening_sell_worker()

임시 플래그: self.sell_worker_done_today = True를 08:59에 세팅하면 아침 루프 전체가 스킵됨(단, 이러면 09:30 강제청산도 안 됨). 오늘 -9%라 수동 모니터링 목적이면 이 플래그로 임시 비활성화 가능. 내일부터 다시 원복.

로그 두 줄만 추가(원인 파악 가속)

파일: _opening_sell_worker() 초기화 직후

logger.info(f"[SELL_WORKER] init: positions_to_sell={list(self.positions_to_sell.keys())}")


파일: 루프 내부

logger.debug(f"[SELL_TICK] {code} cur={current_price} avg={avg_price} open={self.sell_open_prices.get(code)} peak={self.sell_peaks.get(code)}")

왜 이게 핵심이냐

시가/현재가가 0이면 조건식이 전부 무력화된다 → 매도 안 됨. (현재 코드에 “시가 TODO” 주석 존재)

임계값이 높아 트레일/오픈컷이 잘 안 걸린다 → 09:30 몰림.

구독이 늦거나 실패하면 캐시 무(無) → 전부 스킵.

필요하면 위 값들 config에 키 추가해서 네가 장중에 바로 튜닝 가능하게 해둬.

지금보니까 시간이 지날수록 점차 오르는 종목들이 따로 있는듯.. 사조동아원  10% 넘김.. 이거 9:30 매도 빼고 모니터링하면서 팔아야겠다 
ChatGPT의 말:

확인해보니, 네가 말한 “09:30 강제청산 빼고 모니터링하면서 팔기”는 지금 구조상 바로 수정해야 해.

현재 코드 흐름을 보면:

_opening_sell_worker()에서 09:30 도달 시 무조건 전량 시장가 청산이 들어가 있음

integrated_trading_system

.

그 뒤에 sell_worker_done_today = True가 찍히면서 아침 매도 루프가 종료됨

integrated_trading_system

.

수정 포인트

09:30 강제청산 블록 조건 완화

if now.time() >= dt_time(9, 30) and not self.sell_worker_done_today:
    # → config 플래그로 분리
    if self.config.get('trading', {}).get('force_liquidate_at_930', True):
        ...


→ config.trading.force_liquidate_at_930 = False면 강제청산 스킵.

sell_worker_done_today 세팅 지연

지금은 강제청산 끝나야 sell_worker_done_today = True로 바뀌는데,

모니터링 계속하려면 sell_worker_done_today를 바로 세우지 말고, 포지션이 비워질 때만 True로 전환.

익일 확장 모니터링 허용

_is_sell_time()이 09:00~09:30에만 True

integrated_trading_system

인데,

여기를 dt_time(9, 0) <= now.time() < dt_time(15, 20)으로 늘려주면, 장중에도 계속 매도 조건 확인 가능.

즉, 오늘처럼 사조·동아원 같이 09:30 이후 계속 오르는 종목은:

force_liquidate_at_930=False

_is_sell_time() 범위를 장중 전체로 확장

→ 이렇게 하면 오전 9시 이후 종가매수 종목을 네가 원하는대로 계속 모니터링하면서 트레일링으로 팔 수 있어.

원하면 내가 config.yaml에 바로 추가할 키값이랑, 수정 후 예시 코드 블럭까지 정리해줄까?

# 🪝 Swing\_Candidate — 40\~70위 랭킹 모니터 전략 (v2025-09-16)

## TL;DR

* **거래량 Top100** 중 **랭킹 40\~70구간**을 상시 감시하여 “조용히 힘을 모으다 터지는” 종목을 발굴한다.
* 종가매매와 분리: **시간 고정 트리거 없음**, 장중 지속 모니터링 + 시그널 체결.
* 핵심: **랭킹 유지력 + RSI 안정(40\~70) + 1차 파동 이력 + 눌림 후 재도전** + **거래대금/스프레드/섹터RS** 보정.

---

## 1) 문제·범위·성공기준

* 문제: 상위 20\~30위는 상/급락으로 **지속성 낮음**. 중간권(40\~70위)에 **후발 폭발 후보**가 많음.
* 범위: KOSPI/KOSDAQ 현물, 당일 데이터(틱/1분봉), 거래량·거래대금 랭킹 기반.
* 성공: 백테스트(최근 30영업일)에서 **후발 급등 포착률↑**, **슬리피지·체결실패↓**.

---

## 2) 입력·데이터 의존

* 실시간: 틱/1분봉, 체결강도, 최우선호가/스프레드, 거래량/거래대금.
* 일중 랭킹: 거래량 Top100(5분 주기 갱신), 각 종목의 **랭킹 히스토리**.
* 보조: 섹터/지수 데이터(섹터 상대강도 계산용).

---

## 3) 후보 생성 파이프라인

1. **랭킹 필터**: 거래량 Top100 → **랭킹 40\~70**만 추출 (동점 시 거래대금 큰 순).
2. **유동성 하드컷**:

   * 거래대금 ≥ `min_turnover_swing` (기본 30억)
   * 호가 스프레드 ≤ `max_spread_pct_swing` (기본 0.20%)
3. **지속성 필터**:

   * 최근 `persist_window`분 중 **랭킹 40\~70 체류 비율 ≥ p\_keep** (예: 60% 이상)
4. **안정성 필터 (RSI)**:

   * 1분봉 RSI(14) ∈ \[40, 70] 범위 체류율 ≥ r\_keep (예: 60%)
   * 과매수/과매도 구간 체류율이 높으면 제외
5. **1차 파동 이력**:

   * 당일 고점/저점 기준 **최소 +5% 이상 상승 파동 1회** 존재, 이후 **-1%\~-3% 눌림** 거친 종목에 가점
6. **섹터 상대강도(RS)**:

   * 섹터지수 대비 당일 수익률·변동성 조합으로 RS>1.0 가점

---

## 4) 스코어링(0\~100)

```
score = 0.18*RankStability + 0.18*RSIStability + 0.15*FirstWave +
        0.15*VWAP_Premium + 0.12*MoneyIntensity + 0.10*SectorRS +
        0.07*PullbackQuality + 0.05*SpreadPenalty

# 정의
- RankStability: 40~70 구간 체류율(%)를 0~100으로 스케일
- RSIStability: RSI 40~70 체류율(%) 스케일
- FirstWave: 당일 +5% 이상 1차 파동 여부/강도(폭·소요봉수)
- VWAP_Premium: 현재가 vs VWAP 프리미엄 (과열 캡 포함)
- MoneyIntensity: 거래대금(당일) / 최근 5일 평균 거래대금
- SectorRS: (종목 수익률 / 섹터 수익률)·변동성 보정
- PullbackQuality: 눌림폭 1~3% 내 재도전 근접도(고점 이격)
- SpreadPenalty: (스프레드-0.1%)×k → 총점에서 감점
```

---

## 5) 시그널 & 체결 로직

* **관찰 주기**: 1분 (랭킹·지표 업데이트), 5초(체결 체크)까지 허용
* **진입 트리거(예시)**:

  1. score ≥ `enter_score_min`(예: 70)
  2. 가격이 VWAP 위 + 최근 고점 이격 ≤ `rebreak_gap_max`(예: 0.8%)
  3. 최근 3봉 평균 거래량 대비 현재봉 거래량 ≥ 1.5x
* **분할 진입**: 2회(60% + 40%), 2차는 고점 재돌파/거래량 재확인 시
* **손절/익절**:

  * 하드 스탑: 평단 대비 -2.2%
  * 트레일: +0.6% 달성 시 고점대비 -0.4% 이탈 청산
* **시간 가드**: 14:50 이후 신규 진입은 금지(종가매매와 충돌 방지)

---

## 6) 모듈 설계(종가 로직과 분리)

* `strategies/swing_candidate.py`

  * `build_rank_window(top=100, refresh_sec=300)`
  * `pick_midband_candidates(rank_low=40, rank_high=70)`
  * `compute_swing_score(code)`
  * `should_enter(code)`, `should_add(code)`, `should_exit(code)`
* `analytics/swing_dashboard.py`

  * 실시간 테이블: 코드, 이름, 순위, score, VWAP 프리미엄, RS, 스프레드, 시그널 상태
* `risk/swing_guards.py`

  * 스프레드/체결잔량/VI 감지, 시간금지대(14:50\~) 체크
* `core/integrated_trading_system.py`

  * 별도 워커 `/_swing_candidate_worker()` 추가 (종가 워커와 병행)

---

## 7) Config (예시)

```yaml
swing:
  enabled: true
  rank_top_n: 100
  rank_range: [40, 70]
  persist_window_min: 45     # 최근 45분 창
  keep_ratio_min: 0.60       # 40~70 체류 비율
  rsi_period: 14
  rsi_keep_ratio_min: 0.60
  first_wave_min_pct: 0.05   # +5%
  pullback_min_pct: 0.01     # 1%
  pullback_max_pct: 0.03     # 3%
  min_turnover_swing: 3_000_000_000
  max_spread_pct_swing: 0.002
  enter_score_min: 70
  rebreak_gap_max: 0.008
  add_once_only: true
  hard_stop_from_avg: 0.978  # -2.2%
  trail_min_profit: 0.006    # +0.6%
  trail_drop_pct: 0.004      # -0.4%
  block_new_after: "14:50"
```

---

## 8) 의사코드

```python
# 1) 랭킹 윈도우 구축
ranks = get_volume_rank_top100()  # [(code, rank, turnover, t)]
mid = [x for x in ranks if 40 <= x.rank <= 70 and x.turnover >= cfg.min_turnover_swing]

# 2) 지속성 계산
keep_ratio = kept_ratio_in_window(code, window=cfg.persist_window_min, band=(40,70))

# 3) RSI 안정성
rsi = rsi_1m(code, period=cfg.rsi_period)
rsi_keep = kept_ratio(rsi, low=40, high=70, window=cfg.persist_window_min)

# 4) 1차 파동/눌림
fw = first_wave_strength(code, min_pct=cfg.first_wave_min_pct)
pull = pullback_quality(code, min_pct=cfg.pullback_min_pct, max_pct=cfg.pullback_max_pct)

# 5) 보조지표
vwap_prem = (price - vwap) / vwap
money_intensity = today_turnover / avg_turnover_5d
sector_rs = relative_strength_to_sector(code)
spread_pen = max(0, spread_pct - 0.001) * K

score = weights·[keep_ratio, rsi_keep, fw, vwap_prem, money_intensity, sector_rs, pull, -spread_pen]

# 6) 체결 조건
if score >= cfg.enter_score_min and vwap_prem>0 and rebreak_gap(price) <= cfg.rebreak_gap_max and vol_factor>=1.5:
    buy(code, size=0.6*target)
    mark_entered(code)

if entered(code) and !added(code) and rebreak_again_with_vol:
    buy(code, size=0.4*target)

# 7) 청산
if pnl<=-2.2%: sell_all("HardStop")
if pnl>=+0.6% and drop_from_peak>=0.4%: sell_all("TrailStop")
```

---

## 9) 테스트 시나리오

* **리플레이**: 5거래일 틱/1분봉 덤프 → 랭킹 5분 주기 재현, 스코어·트리거 검증
* **엣지**: 랭킹 경계(39/71) 진동, 스프레드 급증, VI/단일가 전환, 뉴스 급등 후 급락
* **메트릭**: 진입 후 평균 보유시간, 승률, 평균수익/손실, 슬리피지, 체결성공률, 재진입 빈도

---

## 10) 운영 체크리스트

* 랭킹·VWAP·RSI·스프레드 계산이 **1분 내 반영**되는지
* 14:50 이후 신규 진입이 차단되는지
* 텔레그램 알림: \[ENTER/ADD/EXIT/STOP] + score + 근거지표 요약

---

## 11) 종가 전략과의 경계

* 종가매매 워커와 **독립 실행**. 포지션 중복 시 우선순위는 `risk/swing_guards.py`에서 관리.
* 동일 종목이 두 전략에 동시 후보로 뜨면, **먼저 체결한 전략**이 소유권을 가짐(중복 매수 금지).


## 네이버 API연동
맞아, 네이버는 “뉴스”가 따로 안 보이고 서비스=검색 안에 뉴스가 들어가 있어. 화면 그대로 진행하면 되고, 환경 설정만 올바르게 잡으면 돼.

딱 이대로 해

사용 API: 검색 선택 (→ 뉴스/블로그/지식iN 등 포함)

비로그인 오픈 API 서비스 환경에서 타입을 골라:

서버: 백엔드(Python, Node)에서 호출할 때 권장.

필수: 공인 IP 입력(고정 IP가 이상적). localhost나 127.0.0.1은 불가.

웹: 브라우저에서 직접 호출할 때.

도메인/URL 화이트리스트에 http://localhost(필요하면 http://localhost:3000 등) 추가 가능.

하지만 네이버 검색 API는 CORS 제한 때문에 브라우저에서 직접 호출은 보통 막혀. → 결국 서버 타입으로 프록시 서버를 두는 게 정석.

결론: 로컬 개발이면

당장은 서버로 만들고, 네 PC가 인터넷 나갈 때 사용하는 공인 IP를 넣어. (검색: “내 IP”로 확인)

공인 IP가 수시로 바뀌면 임시로 클라우드 VM(저사양) 하나 띄우거나, 고정 egress IP가 있는 터널/프록시(예: ngrok 유료, Cloudflare Tunnel+Workers) 쓰는 게 편함.

호출 예시 (뉴스)

엔드포인트: https://openapi.naver.com/v1/search/news.json

헤더:

X-Naver-Client-Id: <CLIENT_ID>

X-Naver-Client-Secret: <CLIENT_SECRET>

쿼리: query(필수), display(≤100), start(≤1000), sort=sim|date

curl -G "https://openapi.naver.com/v1/search/news.json" \
  -H "X-Naver-Client-Id: YOUR_ID" \
  -H "X-Naver-Client-Secret: YOUR_SECRET" \
  --data-urlencode "query=이삭 엔지니어링 계약 연장" \
  --data-urlencode "display=30" \
  --data-urlencode "sort=date"

import requests

ID, SECRET = "YOUR_ID", "YOUR_SECRET"
url = "https://openapi.naver.com/v1/search/news.json"
params = {"query": "TopComedian 웹툰", "display": 30, "sort": "date"}
headers = {"X-Naver-Client-Id": ID, "X-Naver-Client-Secret": SECRET}
r = requests.get(url, params=params, headers=headers, timeout=10)
r.raise_for_status()
for it in r.json().get("items", []):
    print(it["title"], it["originallink"] or it["link"], it["pubDate"])

흔한 막힘 포인트 정리

401/403 뜨면: 환경 타입/공인 IP/도메인 화이트리스트부터 확인.

로컬호스트만 등록하고 서버 타입으로 호출 → 실패함(공인 IP 필요).

브라우저에서 직접 호출 → CORS로 막힘. 반드시 서버에서 호출.

원하면 kis-scalper에 news_fetcher.py/naver_news_client.py 형태로 붙이고, 키는 secrets.json에서 읽어오는 훅이랑 스코어 가점 로직까지 바로 틀 잡아줄게.

## 2025-09-18 추가 개선부분 ::
📌 목적

종가 스코어링에 외국인/기관 수급 동향을 추가 반영.

10분 간격으로 후보군 종목의 최근 1주(5영업일) 데이터를 조회 → “외인 대량 이탈 + 기관/개인 흡수 여부” 점수화.

API 매핑을 명확히 해서 score_monitor에 붙일 수 있는 구조로 정리.

⚙️ 데이터 소스 (KIS Open API)
✅ 필수 API

종목별 투자자매매동향(일별)

개인/외국인/기관 일자별 순매수 (수량/대금)

→ F[d], I[d], P[d] 산출

국내주식 기간별시세(일/주/월/년) 또는 주식일봉분봉조회(일봉)

종가/고가/저가/거래대금

→ 가격 버팀(HoldFlag), 거래대금 분위수

주식당일분봉조회

당일 시가/거래량/거래대금

→ 시초 +%, 거래대금 급증 트리거

🔶 추천 API

종목별 외인·기관 추정가집계

당일 intraday 수급 추정 → 빠른 신호 확인

시장별 투자자매매동향(일별)

코스피/코스닥 전체 수급 흐름 → 레짐 필터 (시장 전체 외인 이탈일 땐 점수 보수적)

국내기관·외국인 매매종목 가집계

상위 매매 종목 리스트 → 워치리스트 보강

🧩 보조 API

프로그램매매 투자자매매동향(당일): 외인/기관과 프로그램 동조 확인

주식기본조회 / 국내주식 기타주요비율: 유통주식수/유통비율 → 유통시총 정규화

🏗️ 점수 피처 정의

F2 = 외국인 순매수대금 (최근 2일 합)

I2 = 기관 순매수대금 (최근 2일 합)

P2 = 개인 순매수대금 (최근 2일 합)

F2n = F2 / FreeFloatMktCap * 100 (% 기준)

InstAbsorb = I2 / |F2|

IndvAbsorb = P2 / |F2|

🧮 점수 규칙 (SupplyScore, 최대 50점)
항목	조건	점수
외인 대량 이탈 강도	F2n ≤ -0.08%	분위수 기준 +5~15
기관 흡수율	InstAbsorb ≥0.7	+6~15
개인 흡수율	IndvAbsorb ≥0.7	+3~6
기관 흡수 보너스	AbsorbByInst=True	+5
가격 버팀	Close[0] ≥ Close[1]*0.97	+5
트리거	시초 +2% / 거래대금 급증	각 +2~3 (최대 +5)

월말/분기말 등 리밸런싱 구간은 점수 ×0.8

최종 점수:

final_score = base_close_score + clamp(SupplyScore, 0, 50)

⏱️ 실행 사이클 (10분 폴링)

후보군 종목에 대해 투자자매매동향(일별) 최근 5영업일 fetch

일봉/기간별시세로 종가/거래대금 업데이트

당일분봉으로 시초/거래량 급증 여부 확인

선택적으로 추정가집계/시장별 동향으로 신호 보정

calc_supply_absorb_score() → supply_score 산출

최종 스코어 = 기존 종가 스코어 + supply_score

📂 코드 구조 제안
analytics/
  └─ supply_score.py        # 피처 생성 + 점수 계산
api/
  └─ kis_investor.py        # 투자자매매동향 REST 어댑터
strategies/
  └─ score_monitor.py       # run_score_monitor() 내 supply_score 통합

함수 스펙
def fetch_investor_trend_daily(api, code, days=5) -> list[dict]:
    # {"date":..., "foreign_amt":..., "inst_amt":..., "indiv_amt":...}
    ...

def build_supply_features(trend_rows, freefloat_mktcap) -> dict:
    # F2, I2, P2, F2n, InstAbsorb, IndvAbsorb 계산
    ...

def calc_supply_absorb_score(feat, close0, close1,
                             open_up_2pct, vol_rank_top20, cfg) -> int:
    # 규칙에 따라 0~50점 산출
    ...

📊 로그 출력 (예시)

logs/supply_signals_YYYY-MM-DD.jsonl

{
  "time": "09:30",
  "code": "A005930",
  "supply_score": 37,
  "features": {
    "F2": -4.2e9,
    "I2": 4.0e9,
    "P2": 0.5e9,
    "F2n": -0.11,
    "InstAbsorb": 0.95,
    "IndvAbsorb": 0.12
  },
  "flags": ["ForeignDump90p", "AbsorbByInst", "HoldOK"]
}

✔️ 매수 조건 예시

supply_score ≥ 25

거래대금 상위 30%

체결강도 ≥ 100

## 최종 수정기획
목적

종가 스코어링의 정확도와 일관성을 높이기 위해
수급(외인·기관) + 힘의 질(CD/VWAP/V30) + 리스크 필터를 결합.

10분 폴링으로 최근 1주(5영업일) 데이터를 갱신, 자동 랭킹/알림.

데이터 소스 (KIS Open API)
필수

종목별 투자자매매동향(일별) → 개인/외국인/기관 일별 순매수(수량/대금)

국내주식 기간별시세(일/주/월/년) 또는 주식일봉분봉조회(일봉) → 종가/거래대금

주식당일분봉조회 → 당일 시가/고가/VWAP용 분봉, 거래대금 급증

추천(보강)

종목별 외인·기관 추정가집계 → Intraday 수급 보정

시장별 투자자매매동향(일별) → 레짐 필터(시장 전체 외인 이탈 시 보수적 가중)

국내기관·외국인 매매종목 가집계 → 후보군 보강

프로그램매매 투자자매매동향(당일/일별) → 수급 동조 가점/감점

주식기본조회 / 국내주식 기타주요비율 → 유통주식수/유통비율(유통시총 정규화)

실행 주기 / 파이프라인 (10분)

후보군 N종목에 대해 투자자매매동향(일별) 5영업일 Pull(캐시)

일봉/기간별시세로 Close/거래대금 갱신

당일분봉으로 VWAP·V30·오프닝 변동 추출

(선택) 추정가집계/시장별 수급/프로그램으로 보정

calc_supply_absorb_score() + calc_quality_score() → 합산

랭킹/로그/텔레그램 알림

스코어 구성
final_score = base_close_score
            + SupplyScore(최대 50)
            + QualityScore(최대 40)
            - RiskPenalty(최대 20)

1) SupplyScore (외인·기관 수급, 최대 50)

표기: d=0(당일),1(전일)… / 2일 합 기본

정의

F[d], I[d], P[d]: 외국인/기관/개인 순매수대금(원)

F2 = F[0]+F[1], I2 = I[0]+I[1], P2 = P[0]+P[1]

FreeFloatMktCap: 유통시가총액(원)

F2n = 100 * F2 / FreeFloatMktCap (단위 %)

InstAbsorb = I2 / |F2|, IndvAbsorb = P2 / |F2|

점수 규칙

외인 대량 이탈 강도: F2n ≤ -0.08%

후보군 분포 분위수로 가점: 60p:+5 / 80p:+10 / 90p:+15

기관 흡수율 InstAbsorb

0.7~0.9:+6 / 0.9~1.1:+10 / 1.1~1.5:+12 / >1.5:+15

개인 흡수율 IndvAbsorb

0.7~0.9:+3 / 0.9~1.1:+5 / >1.1:+6 (기관 대비 0.5배 가중)

기관 흡수 보너스: InstAbsorb ≥ 0.7 → +5

가격 버팀: Close[0] ≥ Close[1]*0.97 → +5

트리거 보너스(선택): 시초 +2% / 당일 거래대금 상위 20위 내 → 각 +2~3 (합계 +5)

보정

월말/분기말 리밸런싱: 전체 점수 ×0.8

프로그램매매가 외인/기관과 동시 순매도면 SupplyScore ×0.9, 동시 순매수면 +3

2) QualityScore (힘의 질, 최대 40)

지표 정의(당일 분봉 기반)

Closing Drive (CD): 15:00~15:20 가격 기울기(선형회귀 기울기 ÷ 가격)

상위 분위수 가점: 60p:+6 / 80p:+9 / 90p:+12

VWAP 프리미엄 (PVAP): (Close - VWAP) / VWAP

0~0.3%:+3 / 0.3~0.8%:+6 / 0.8~1.5%:+9 / >1.5%:+12

막판 거래량 비중 (V30): 15:00~15:30 거래량 / 일중 총거래량

10~15%:+3 / 15~20%:+5 / 20%~:+8

전고 돌파 플래그: 당일 고가 ≥ 전일 고가 → +4

3) RiskPenalty (리스크 패널티, 최대 20)

유동성 패널티: 호가 스프레드/틱가치 기반

스프레드비율 0.4~0.6%: -4 / 0.6~0.8%: -7 / >0.8%: -10

과열 패널티: 당일 등락률 ≥ +15% → -10 (다음날 갭다운 리스크)

저유동성 차단: 일거래대금 하위 20% → -10 또는 즉시 제외

뉴스/공시 이벤트 플래그(합병/유증/CB 등) → -5~-10 (화이트리스트 예외)

후보 선정 & 포지션 배분

매수 허용 조건(예시)

SupplyScore ≥ 25 AND QualityScore ≥ 18

거래대금 상위 30% AND 체결강도 ≥ 100

랭킹 Top K (기본 5종목) 선별 후 Softmax 가중 배분

w_i = exp(final_score_i / τ) / Σ exp(...), τ=10~15

상한: 단일 종목 40% 캡, 하한: 10% 미만은 스킵 가능

텔레그램 알림 (예시 포맷)
[종가 스코어링 결과] 09:30

1) 심리문투 (45,700)  🟢  총점 87
  - Supply 46 (외인-0.11%, 기관흡수0.95, 버팀OK)
  - Quality 31 (CD 상위80p, PVAP 0.9%, V30 18%)
  - Risk  - - - (스프레드 0.22%)
  - 배분 28%

2) ABC전자 (12,350)  총점 81
  - Supply 40 / Quality 29 / Risk - -4
  - 배분 24%
...

설정 (config.yaml 제안)
supply_score:
  poll_minutes: 10
  lookback_days: 5
  sum_days: 2
  foreign_dump_pct_thr: 0.08
  absorb_ratio_thr: 0.7
  hold_thr: 0.97
  regime_weight:
    market_dump_day: 0.8
  caps:
    max_supply_score: 50

quality_score:
  cd_window: "15:00-15:20"
  vwap_min_candles: 30
  v30_window: "15:00-15:30"
  caps:
    max_quality_score: 40

risk:
  spread_penalty:
    buckets: [0.004, 0.006, 0.008]
    points:  [4, 7, 10]
  overheat_threshold: 0.15
  illiquid_bottom_pct: 0.2
  caps:
    max_risk_penalty: 20

allocation:
  top_k: 5
  tau: 12
  per_symbol_cap: 0.4
  min_weight: 0.1

로그 스키마

logs/supply_signals_YYYY-MM-DD.jsonl
logs/quality_signals_YYYY-MM-DD.jsonl
필드(공통):

{
  "time":"09:30",
  "code":"A005930",
  "scores":{"supply":37,"quality":29,"risk":4,"final":62},
  "supply":{"F2":-4.2e9,"I2":4.0e9,"P2":0.5e9,"F2n":-0.11,"InstAbsorb":0.95,"IndvAbsorb":0.12,"hold":true},
  "quality":{"cd":0.0042,"pvap":0.009,"v30":0.18,"prev_high_break":true},
  "risk":{"spread":0.0022,"overheat":false,"illiquid":false},
  "flags":["ForeignDump90p","AbsorbByInst","CD80p","PVAP0.8p","HoldOK"]
}

테스트 체크리스트

A/B 비교: SupplyScore만 vs Supply+Quality+Risk

민감도: sum_days∈{2,3}, absorb_ratio_thr∈{0.6,0.7,0.9}, τ∈{10,12,15}

달의 말일/분기말: 리밸런싱 보정 작동 확인(×0.8)

저유동/광폭변동: 차단이 제대로 되는지

텔레그램: 점수 구성요소/배분 비중이 함께 표기되는지
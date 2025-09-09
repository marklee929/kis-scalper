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



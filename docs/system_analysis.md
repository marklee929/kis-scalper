# 통합 트레이딩 시스템 분석 보고서

## 1. 현재 프로그램 요약

- **데이터 수집**: `core.integrated_trading_system.IntegratedTradingSystem`은 KIS API를 통해 거래대금 상위 종목(`get_turnover_ranking`)과 실시간 호가(`market_cache.get_quote_full`)를 취득합니다.【F:core/integrated_trading_system.py†L11-L140】【F:core/integrated_trading_system.py†L320-L398】
- **종목 선정**: 기존 로직은 `strategies.closing_price_trader.closing_price_stock_filter`로 종가 전략 후보를, `strategies.swing_screener.get_swing_candidates`로 스윙 후보를 산출하고 거래대금 상위 종목을 하드코딩된 fallback 로직으로 보완했습니다.【F:core/integrated_trading_system.py†L320-L398】【F:strategies/closing_price_trader.py†L20-L180】
- **매수/매도 조건**:
  - **매도**: 오전 9시 이후 시가/평균가 대비 손절·트레일링 스탑·수익 실현 비율을 비교해 시장가 매도를 실행합니다.【F:core/integrated_trading_system.py†L176-L276】
  - **매수**: 15:18~15:29 사이 점수 기반 Softmax 가중치로 예산을 배분하고, 지정가-시장가 혼합(Limit-then-Market) 주문을 발주합니다.【F:core/integrated_trading_system.py†L586-L704】
- **보조 기능**: 뉴스 모니터링(`strategies.news_handler`), 포지션 관리(`core.position_manager.RealPositionManager`), 텔레그램 알림(`utils.notifier`)을 제공합니다.【F:core/integrated_trading_system.py†L398-L586】

## 2. 코드 내 하드코딩된 주요 값

| 구분 | 설명 | 위치 |
| --- | --- | --- |
| 시간 조건 | 매도 시간대(09:00~15:20), 스크리닝(09:30~15:20), 매수(15:18~15:29) | `IntegratedTradingSystem._is_sell_time/_is_screening_time/_is_buy_time`【F:core/integrated_trading_system.py†L120-L134】 |
| 매도 규칙 | 손절·트레일링 비율, 초기 시가 손절 등 | `IntegratedTradingSystem._check_sell_conditions`【F:core/integrated_trading_system.py†L190-L252】 |
| 후보 수 | 거래대금 상위 100개 조회 및 Fallback 상위 5개 | `IntegratedTradingSystem._closing_price_screening_worker` (기존)【F:core/integrated_trading_system.py†L320-L398】 |
| 전략 지표 | 이동평균·거래대금 임계값 등 | `strategies/closing_price_trader.py` 전역 상수 |【F:strategies/closing_price_trader.py†L20-L120】|
| 리스크 한도 | 최대 포지션, 손실 한도, 고정 손절/익절 비율 | `strategies/risk_management.py`의 기본값 |【F:strategies/risk_management.py†L7-L76】|
| 구성 값 | `config/strategy_settings.yaml` 도입 전에는 JSON 내 고정 배열/수치 사용 | `core/config.py` |【F:core/config.py†L20-L168】|

## 3. 개선 목표 대비 현 상태 요약

- 종목 선정은 고정된 거래대금 기준과 수동 필터에 의존하여 시장/섹터/펀더멘털/이벤트 정보가 반영되지 않았습니다.
- 자동 매수·매도 전략은 단일 종가 전략 중심으로 골든크로스, RSI, 볼린저 밴드 등 복수 전략 통합이 어려웠습니다.
- 리스크 관리 및 포지션 사이징이 고정 비율로 하드코딩되어 있었으며, 부분 청산/트레일링 설정이 미흡했습니다.
- 설정 값이 코드 내 상수로 존재해 전략 파라미터 변경이 어려웠습니다.

이후 커밋에서는 위 문제를 해결하기 위해 전략 설정 파일(YAML), 동적 스크리너, 다중 전략 엔진, 리스크 관리 개선, 주문 계획 로깅 등을 도입합니다.

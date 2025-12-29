# Market Snapshot Schema (Immutable)

Snapshot은 시스템 전체의 공통 언어다.
전략(Entity)은 오직 Snapshot만 본다.

## Identity
- snapshot_id (uuid)
- timestamp (ms)
- source (paper / real)
- seed (재현성)

## Price
- last_price
- open
- high
- low
- prev_close
- price_change
- price_change_rate

## Volume
- volume
- volume_rate
- trade_count

## Orderbook (compressed)
- best_bid
- best_ask
- spread
- bid_depth_sum (top N)
- ask_depth_sum (top N)

## Volatility
- atr
- atr_rate
- intraday_vol
- volatility_spike_flag

## Regime
- regime_label
- regime_confidence

## News Signal
- news_event_type
- news_severity
- news_relevance

## System Health
- api_latency_ms
- ws_connected (bool)
- error_rate
- slippage_estimate

## Portfolio (read-only)
- cash
- equity
- exposure
- positions_summary

### Rules
- Snapshot은 생성 후 절대 변경 불가
- Entity는 Snapshot을 캐싱만 가능
- Snapshot 버전은 반드시 로그에 남긴다

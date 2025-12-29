# Evolution Log Examples

## Action Log
```json
{
  "timestamp": 1712345678901,
  "snapshot_id": "abc-123",
  "entity_id": "momentum_v1",
  "generation": 3,
  "action": "BUY",
  "size": 100,
  "reason": "breakout_signal",
  "confidence": 0.72
}
```

## Result Log

```json
{
  "timestamp": 1712345680000,
  "snapshot_id": "abc-123",
  "entity_id": "momentum_v1",
  "fill_price": 72100,
  "slippage": 0.15,
  "fee": 120,
  "pnl_delta": -3500,
  "drawdown_delta": 0.004
}
```

## Death Log

```json
{
  "timestamp": 1712346000000,
  "entity_id": "momentum_v1",
  "death_type": "MAX_DAILY_LOSS",
  "trigger": "loss_limit",
  "regime": "volatility_spike",
  "news_severity": 0.8
}
```

## Hibernation Record

```json
{
  "lineage_id": "trend_family",
  "generation_id": 3,
  "sealed_at": "2025-03-01",
  "reason": "repeat_death_in_volatility",
  "reactivation_condition": "low_vol_trend"
}
```

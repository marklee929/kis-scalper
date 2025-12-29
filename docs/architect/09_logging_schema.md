# Evolution Logging Schema

로그는 디버깅용이 아니라
진화를 위한 기억이다.

모든 로그는 다음 6개를 반드시 포함한다.

1. Market Snapshot
- timestamp
- price / volume / volatility
- orderbook summary
- regime label

2. Entity State
- entity_id
- generation
- parameters hash
- risk_state

3. Action
- action_type (buy/sell/hold)
- size
- reason_tag (strategy_id)

4. Result
- fill_price
- slippage
- fee
- pnl_delta
- drawdown_delta

5. Death Event (optional)
- death_type
- trigger (loss, volatility, api, etc)

6. Context
- news_signal
- system_state

로그가 없으면
죽음은 의미를 잃는다.

# Evolution Scoring

스코어는 “얼마 벌었나”가 아니다.
“얼마나 안 죽었나”가 중심이다.

## Base Metrics
- total_pnl
- max_drawdown
- death_count
- avg_slippage
- trade_count

## Regime-aware Metrics
- pnl_by_regime
- death_by_regime
- exposure_by_regime

## Score Formula (Example)
score =
  + w1 * normalized_pnl
  - w2 * max_drawdown
  - w3 * death_count
  - w4 * slippage_penalty
  - w5 * overtrading_penalty

## Hard Fail
- death_count > N
- drawdown > threshold
→ automatic seal / demotion

## Usage
- 일 단위 스코어
- 세대 비교
- 승격/동면 판단

# Codebase Mapping (kis_scalper)

기존 kis_scalper는
단일 루프 중심 구조였다.

Remodeling 매핑:

[ 기존 ]
- main.py
- score_monitor.py
- watch_holding()
- is_rising_now()

[ 재구성 ]
- environment/ (Java)
  - api_adapter
  - event_loop
  - risk_gate
- entities/ (Python)
  - entity_base
  - presets/
- evolution/
  - scorer
  - selector
  - hibernation
- logs/
  - evolution_log
  - death_log
- dashboard/
  - system_state
  - entity_state

기존 로직은
“전략”이 아니라
“초기 개체 프리셋”으로 흡수된다.

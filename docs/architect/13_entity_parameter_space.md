# Entity Parameter Space

초기 개체들은 “다른 모델”이 아니라
같은 골격을 공유하는 서로 다른 성향이다.

공통 골격:
- 동일 입력 스냅샷
- 동일 출력 인터페이스
- 동일 리스크 게이트

초기 3개 성향 프리셋:

[ A: Momentum ]
- entry_sensitivity: high
- hold_time: long
- stop_loss: wide
- trailing: on
- max_exposure: medium
- cooldown: short

[ B: Mean Reversion ]
- entry_sensitivity: low
- hold_time: short
- stop_loss: tight
- trailing: off
- max_exposure: low
- cooldown: medium

[ C: Survival / Risk-Off ]
- entry_sensitivity: very_low
- hold_time: minimal
- stop_loss: very_tight
- max_exposure: very_low
- cooldown: long
- veto_power: true

파라미터 변경은
- 장후
- 1~2개 항목만
- 변화량 상한을 둔다

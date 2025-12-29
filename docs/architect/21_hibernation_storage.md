# Hibernation Storage (세대/혈통 보존)

전략은 삭제하지 않는다.
동면시킨다.

## Concepts
- Lineage: 같은 구조(골격)를 공유하는 혈통
- Generation: 혈통 내부의 세대(파라미터/규칙 변형)
- Seal: 봉인 태그(왜 동면했는지)

## Storage Objects
1) lineage.json
- lineage_id
- base_architecture_version
- allowed_inputs (snapshot fields)
- creation_date

2) generation.json
- generation_id
- parent_generation_id
- parameter_hash
- parameters
- training_window
- known_strengths (regimes)
- known_weaknesses (regimes)
- seal_status (active/hibernated/extinct)

3) seal_record.json
- sealed_at
- reason (repeat_death, paradigm_mismatch, liquidity_issue ...)
- evidence pointers (log ids)
- reactivation_conditions (regime_signature)

## Reactivation Policy
- 유사 환경 감지 시:
  - OBSERVE → SHADOW → ACTIVE
- 즉시 ACTIVE 금지

## Extinction vs Hibernation
- Extinct: 구조적으로 반복 사망 (종 자체 문제)
- Hibernated: 환경이 안 맞음 (시대가 다름)

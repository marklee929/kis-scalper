TickEvent 스트림을 받아 1초/1분 바를 만들고, feature_builder로 observation을 만든 뒤,
3개 모델이 act()로 액션을 내고, paper_broker가 체결 시뮬레이션을 수행하며,
portfolio가 PnL/수수료/슬리피지를 반영하고, env가 reward를 계산해 transition 로그를 저장하도록 만들어라.
- 모델 3개는 처음엔 룰 기반(stub) + 간단한 online update(가중치 조정)만 구현
- transition 로그는 jsonl로 저장(모델별 파일)
- daily summary도 생성
- main_realtime.py 하나로 실행 가능해야 한다.

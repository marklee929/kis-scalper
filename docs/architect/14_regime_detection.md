# Regime Detection

레짐은 예측 대상이 아니라
분류 대상이다.

레짐 분류 목적:
- 어떤 개체가 활동할 자격이 있는지 결정

기본 레짐 타입:
- trend
- range
- volatility_spike
- crash
- news_driven

입력 신호:
- 변동성 지표
- 거래량 급변
- 가격 가속도
- 뉴스 severity
- 체결 실패율

출력:
- current_regime
- confidence
- allowed_entities[]

레짐 감지는
트레이딩을 직접 지시하지 않는다.
활동 허가만 한다.

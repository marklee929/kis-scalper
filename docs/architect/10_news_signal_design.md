# News Signal Design

뉴스는 판단이 아니라
환경 신호다.

트레이딩 개체는
텍스트를 읽지 않는다.

Pipeline:
- 뉴스 수집 (Naver API 등)
- 제목 기반 분류
- 이벤트 타입 라벨링
- 수치 신호화 후 전달

최소 출력:
- event_type (capital, disaster, earnings, contract, regulation, noise)
- sentiment (pos / neg / neu)
- severity (0.0 ~ 1.0)
- relevance (0.0 ~ 1.0)

텍스트는 분류기에만 사용되고
저장은 숫자만 남긴다.

뉴스는 생각의 재료가 아니라
반사의 트리거다.

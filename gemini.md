📄 gemini.md – Swing 종목 선정 개선안
🎯 목적

기존 거래량 순위 기반 필터(40~70위 등) 한정에서 벗어나,

전체 종목에서 잠잠하다가 순간 폭발하는 패턴을 실시간으로 잡아내는 로직으로 개선.

스윙 종목은 단순히 “많이 오른 주식”이 아니라, 상승 전환 + 체결강도 동반 + 거래량 폭발 조건 충족 시 진입 후보로 선정.

⚙️ 개선 핵심 로직
1. 전체 종목 대상 1차 필터

ETF/ETN/우선주/잡주 제외 (기존 EXCLUDE_KEYWORDS 유지)

거래대금 10억 이상 종목만 남기기 → 유동성 확보

2. 실시간 거래량 변화율 (ΔVolume)

최근 1분 거래량 / 직전 5분 평균 거래량 ≥ 3배 이상

단순 거래량 순위가 아닌, 폭발률 기반 점수 계산

지연 없이 즉각 후보 리스트에 추가

3. 체결강도 & 호가 비율 확인

체결강도 ≥ 120% 이상 (매수 우위)

매수호가 잔량 / 매도호가 잔량 ≥ 1.2

4. 가격 추세 필터

현재가 / 직전 5분 저가 ≥ +1% 이상 상승

고점대비 괴리율 ≤ 2% (너무 고평가된 종목 제외)

5. 점수화 스키마

ΔVolume 폭발률: 0~50점

체결강도: 0~30점

상승률(단기 추세): 0~20점

총점 ≥ 70점 → 스윙 후보 등록

📊 동작 시나리오

장 시작 5분 이후, 전체 종목 WebSocket 구독 시작

30초마다 거래량/체결강도/가격변화 체크

위 점수 기준 충족 종목만 logs/swing_candidates_YYYY-MM-DD.json 저장

모니터링 루프에서 최종 5~10개 종목만 남김

🛠️ 구현 구조 (예시)

strategies/swing_filter.py

def swing_stock_filter(market_cache, candidates, api):
    """스윙 적합 종목 필터링"""
    results = []
    for stock in candidates:
        code = stock["code"]
        name = stock.get("name", "")
        # 1️⃣ ETF/잡주 제외
        if any(k in name for k in EXCLUDE_KEYWORDS):
            continue
        # 2️⃣ 거래량 변화율
        vol_ratio = calc_volume_ratio(code, market_cache)
        if vol_ratio < 3: 
            continue
        # 3️⃣ 체결강도
        strength = get_strength(code, market_cache)
        if strength < 120: 
            continue
        # 4️⃣ 상승 전환
        if not is_price_breakout(code, market_cache):
            continue
        results.append(stock)
    return results


logs/swing_candidates_YYYY-MM-DD.json 저장 후 main.py에서 구독 업데이트

🚀 기대 효과

단순 순위 컷 제한(40~70위)을 없애고,

“잠잠하다가 순간 치는” 종목을 실시간 포착 가능

스윙 전략에서 폭발 구간 초입 진입 확률 증가

불필요한 잡주/테마주 제외로 승률 안정성 강화

👉 이 문서를 기준으로 score_monitor + swing_filter 두 갈래로 나눠서 관리 가능.
하나는 단타/스캘핑용 (score_monitor), 하나는 스윙용 (swing_filter).
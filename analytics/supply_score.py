
from typing import Dict, List
import logging
import numpy as np

logger = logging.getLogger(__name__)

def build_supply_features(trend_rows: List[Dict], freefloat_mktcap: float) -> Dict:
    """
    일별 투자자 동향 데이터로부터 수급 관련 피처를 생성합니다.
    F2n (유통 시총 대비 2일 외인 순매수), InstAbsorb (기관 흡수율) 등을 계산합니다.
    """
    if not trend_rows or len(trend_rows) < 2:
        return {}

    try:
        # 최근 2일 합산 순매수 대금
        f2 = sum(item.get('foreign_amt', 0) for item in trend_rows[:2])
        i2 = sum(item.get('inst_amt', 0) for item in trend_rows[:2])
        p2 = sum(item.get('indiv_amt', 0) for item in trend_rows[:2])

        # 유통 시가총액 대비 외인 순매수 비율 (%)
        f2n = (f2 / freefloat_mktcap * 100) if freefloat_mktcap > 0 else 0

        # 외인 매도 물량 대비 기관/개인 흡수율
        inst_absorb = (i2 / abs(f2)) if f2 < 0 else 0
        indv_absorb = (p2 / abs(f2)) if f2 < 0 else 0

        features = {
            "F2": f2,
            "I2": i2,
            "P2": p2,
            "F2n": f2n,
            "InstAbsorb": inst_absorb,
            "IndvAbsorb": indv_absorb
        }
        return features

    except Exception as e:
        logger.error(f"수급 피처 생성 중 오류: {e}", exc_info=True)
        return {}

def calc_supply_absorb_score(features: Dict, daily_data: Dict, config: Dict) -> int:
    """
    수급 피처와 일별 데이터를 바탕으로 최종 수급 점수(0~100)를 계산합니다.
    gemini.md의 점수 규칙을 기반으로 합니다.
    """
    if not features:
        return 0

    score = 50  # 기본 점수
    flags = []

    try:
        # 외인 대량 이탈 강도 (F2n <= -0.08%)
        if features.get('F2n', 0) <= -0.08:
            score += 15
            flags.append("ForeignDump")

        # 기관 흡수율 (InstAbsorb >= 0.7)
        if features.get('InstAbsorb', 0) >= 0.7:
            score += 20
            flags.append("InstAbsorb")
        
        # 개인 흡수율 (IndvAbsorb >= 0.7) - 기관 흡수보다는 낮은 가중치
        if features.get('InstAbsorb', 0) < 0.5 and features.get('IndvAbsorb', 0) >= 0.7:
            score += 5
            flags.append("IndvAbsorb")

        # 가격 버팀 (전일 종가 대비 -3% 이상 하락하지 않음)
        if daily_data.get('close', 0) >= daily_data.get('prev_close', 0) * 0.97:
            score += 10
            flags.append("HoldOK")

        # 거래대금 급증 (거래대금 상위 20위 이내)
        if daily_data.get('turnover_rank', 999) <= 20:
            score += 5
            flags.append("VolSpike")

        # 최종 점수 클리핑 (0 ~ 100)
        final_score = int(np.clip(score, 0, 100))
        logger.debug(f"Supply Score: {final_score}, Flags: {flags}, Features: {features}")
        return final_score

    except Exception as e:
        logger.error(f"수급 점수 계산 중 오류: {e}", exc_info=True)
        return 0

# 사용 예시
if __name__ == '__main__':
    sample_features = {
        'F2': -4200000000.0, 'I2': 4000000000.0, 'P2': 50000000.0, 
        'F2n': -0.11, 'InstAbsorb': 0.95, 'IndvAbsorb': 0.01
    }
    sample_daily_data = {
        'close': 70000, 'prev_close': 71000, 'turnover_rank': 15
    }
    
    score = calc_supply_absorb_score(sample_features, sample_daily_data, {})
    print(f"계산된 수급 점수: {score}") # 예상 점수: 50 + 15(F2n) + 20(Inst) + 10(Hold) + 5(Vol) = 100

from utils.logger import logger
from pykrx import stock
import pandas as pd
import datetime

def get_latest_trading_day():
    """시점(장중/장후)과 주말/공휴일을 고려하여 가장 최근의 거래일을 YYYYMMDD 형식으로 반환"""
    now = datetime.datetime.now()
    base_date = now.date()

    # 장 마감(15:30) 이후 일정 시간(16:00)이 지나야 당일 데이터가 확정된 것으로 간주
    if now.time() < datetime.time(16, 0):
        base_date -= datetime.timedelta(days=1)

    # base_date부터 시작하여 유효한 거래일을 찾을 때까지 하루씩 뒤로 이동
    for i in range(10): # 최대 10일 전까지만 탐색
        check_date = base_date - datetime.timedelta(days=i)
        
        date_str = check_date.strftime("%Y%m%d")

        try:
            # 해당 날짜의 시가총액 데이터 조회를 시도하여 거래일인지 확인
            # KOSPI 시장만 조회해도 전체 장이 열렸는지 확인 가능
            df_marketcap = stock.get_market_cap(date_str, market="KOSPI")
            
            # pykrx가 휴일에 0으로 채워진 DF를 반환하므로, 실제 거래가 있었는지 확인
            if not df_marketcap.empty and df_marketcap['거래대금'].sum() > 0:
                logger.info(f"✅ 최종 거래일 확인: {date_str}")
                return date_str
            logger.debug(f"{date_str}는 거래일이 아님 (거래 데이터 없음).")
        except Exception as e:
            # pykrx에서 휴일 등의 이유로 오류 발생 시 다음 날짜로 넘어감
            logger.debug(f"{date_str}는 거래일이 아님. ({e})")
            continue
            
    logger.error("❌ 최근 10일 내에 유효한 거래일을 찾지 못했습니다.")
    return None # 실패 시 None 반환

def code_loader(
    turnover_thr=1e9,
    min_marketcap=2000e8,  # 시가총액 2,000억
    min_pct_change=0.01, # 최소 1% 상승
    top_n=50 # 상위 N개 종목 선택
):
    """
    pykrx를 사용하여 전일 데이터 기준으로 관심 종목을 선정합니다.
    기존의 엄격한 필터 방식 대신, 기본 필터링 후 점수 기반으로 상위 N개 종목을 선정하여 안정성을 높였습니다.
    """
    today = get_latest_trading_day()
    if not today:
        logger.error("최근 거래일을 가져올 수 없어 code_loader를 중단합니다.")
        return pd.DataFrame()
    logger.info(f"오늘 날짜: {today}")
    df = stock.get_market_ohlcv(today, market="ALL")
    if df.empty:
        logger.warning(f"{today}자 OHLCV 데이터가 비어 있습니다.")
        return pd.DataFrame()

    # 시가총액 데이터 가져와서 병합
    try:
        mcap = stock.get_market_cap(today, market="ALL")[['시가총액']]
        # Check if '시가총액' already exists in df and drop it to avoid overlap
        if '시가총액' in df.columns:
            df = df.drop(columns=['시가총액'])
        df = df.join(mcap, how='inner')
    except Exception as e:
        logger.error(f"시가총액 데이터 로드 또는 병합 실패: {e}")
        # 시가총액 없이 진행하거나, 여기서 중단할 수 있음. 우선은 중단.
        return pd.DataFrame()

    # 파생 지표
    df['pct']        = df['종가'] / df['시가'] - 1
    df['volatility'] = (df['고가'] - df['저가']) / df['시가']
    df['turnover']   = df['종가'] * df['거래량']
    df['close_high_ratio'] = df['종가'] / df['고가']
    df['range'] = (df['고가'] - df['저가']) / df['저가']

    # 시가총액 필터 추가!
    df = df[df['시가총액'] >= min_marketcap]
    # 거래대금 최소 필터
    df = df[df['turnover'] >= turnover_thr]

    if df.empty:
        logger.warning(f"기본 필터(시총, 거래대금)를 만족하는 종목이 없습니다.")
        return pd.DataFrame()

    # 최소 상승률 조건으로 기본 필터링
    filtered = df[df['pct'] >= min_pct_change].copy()

    if filtered.empty:
        logger.warning(f"{min_pct_change*100}% 이상 상승하고 기본 필터를 만족하는 종목이 없습니다.")
        return pd.DataFrame()

    sel = filtered.reset_index()
    sel.rename(columns={sel.columns[0]: '종목코드', '종가': '현재가'}, inplace=True)
    sel['종목코드'] = sel['종목코드'].astype(str).str.zfill(6)
    sel['등락률']   = (sel['pct'] * 100).round(2)
    sel['종목명']   = sel['종목코드'].apply(stock.get_market_ticker_name)

    # 점수 계산 (모든 후보군에 대해)
    # 거래량 정규화를 위해 filtered['거래량'].max() 대신 df['거래량'].max() 사용 가능하나,
    # 여기서는 필터된 종목군 내에서의 상대적 비교를 위해 그대로 둡니다.
    sel['차일상승가능성'] = (
        sel['등락률'] * 0.3 +
        (sel['현재가'] / sel['고가']) * 30 +
        (sel['거래량'] / sel['거래량'].max()) * 30 +
        sel['volatility'] * 100 * 0.1
    ).round(1)

    # 점수 기준으로 정렬 후 상위 N개 선택
    top_sel = sel.sort_values('차일상승가능성', ascending=False).head(top_n)

    save_df = top_sel[['종목명','종목코드','현재가','등락률','고가','저가','시가총액','차일상승가능성']].copy()
    out_path = f"logs/sector_filtered_{datetime.date.today().isoformat()}.json"
    save_df.to_json(out_path, force_ascii=False, orient='records', indent=2)
    logger.info(f"저장 완료: {out_path} ({len(save_df)}개 종목)")

    return save_df

if __name__ == "__main__":
    top = code_loader(
        turnover_thr=10e8,
        min_marketcap=2000e8,
        top_n=20
    )
    if not top.empty:
        print(top[['종목명','종목코드','현재가','등락률','고가','저가','시가총액','차일상승가능성']].head(10))
    else:
        print("조건을 만족하는 종목이 없습니다.")
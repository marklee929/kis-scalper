"""시장 데이터 공급자 추상화 모듈."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List, Optional

import logging

import pandas as pd
from requests import Session
from requests.exceptions import SSLError as RequestsSSLError

try:  # pragma: no cover - urllib3는 requests 내부 의존성
    from urllib3.exceptions import SSLError as Urllib3SSLError
except ModuleNotFoundError:  # pragma: no cover
    Urllib3SSLError = tuple()  # type: ignore[assignment]

import time

import certifi

logger = logging.getLogger(__name__)


@dataclass
class FundamentalSnapshot:
    """기본적 지표 스냅샷."""

    symbol: str
    debt_to_equity: float
    current_ratio: float
    cash_to_operating_expense_months: float
    revenue_growth: float
    eps_growth: float


@dataclass
class CorporateEvent:
    """기업 이벤트 정보."""

    symbol: str
    event_type: str
    timestamp: datetime
    headline: str
    url: Optional[str] = None


class MarketDataDownloadError(RuntimeError):
    """시장 데이터 다운로드 실패 예외."""


class MarketDataProvider(ABC):
    """시장 데이터 공급자를 위한 추상 기반 클래스."""

    @abstractmethod
    def get_daily_history(
        self,
        symbol: str,
        lookback_days: int,
        end: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """일봉 데이터 프레임을 반환합니다."""

    @abstractmethod
    def get_intraday_history(
        self,
        symbol: str,
        period: str = "5d",
        interval: str = "1m",
    ) -> pd.DataFrame:
        """분봉 데이터 프레임을 반환합니다."""

    @abstractmethod
    def get_average_volume(self, symbol: str, window: int) -> float:
        """지정된 기간 동안의 평균 거래량."""

    @abstractmethod
    def get_sector_performance(self, lookback_weeks: int) -> pd.DataFrame:
        """섹터별 수익률 데이터."""

    @abstractmethod
    def get_fundamentals(self, symbol: str) -> FundamentalSnapshot:
        """기본적 지표를 반환합니다."""

    @abstractmethod
    def get_recent_events(self, symbol: str) -> List[CorporateEvent]:
        """최근 이벤트 목록."""

    @abstractmethod
    def stream_quotes(self, symbols: Iterable[str], interval: str = "1m") -> Iterable[pd.DataFrame]:
        """실시간/의사실시간 시세를 스트리밍합니다."""


class YFinanceDataProvider(MarketDataProvider):
    """yfinance 기반 데이터 공급자 구현.

    네트워크가 차단된 환경에서는 동작하지 않으며, 해당 경우에는
    호출 시 예외를 발생시켜 상위 로직에서 처리하도록 합니다.
    """

    def __init__(
        self,
        session: Optional[Session] = None,
        *,
        max_retries: int = 3,
        retry_backoff: float = 1.5,
        verify: bool = True,
        cert_path: Optional[str] = None,
    ):
        try:
            import yfinance as yf  # type: ignore

            self._yf = yf
        except ModuleNotFoundError as exc:  # pragma: no cover - 런타임 의존성
            raise RuntimeError("yfinance 패키지가 설치되어 있지 않습니다.") from exc

        self._session: Session = session or Session()
        if verify:
            self._session.verify = cert_path or certifi.where()
        else:
            self._session.verify = False  # type: ignore[assignment]

        self._max_retries = max(1, max_retries)
        self._retry_backoff = max(0.1, retry_backoff)

    def get_daily_history(self, symbol: str, lookback_days: int, end: Optional[datetime] = None) -> pd.DataFrame:
        end = end or datetime.utcnow()
        start = end - pd.Timedelta(days=lookback_days)
        logger.debug("[데이터] %s 일봉 다운로드 (%s~%s)", symbol, start.date(), end.date())
        try:
            data = self._download(symbol, start=start, end=end, interval="1d")
        except MarketDataDownloadError as exc:
            logger.error("[데이터] %s 일봉 다운로드 실패: %s", symbol, exc)
            return pd.DataFrame()
        if data.empty:
            logger.warning("[데이터] %s 일봉 데이터가 비어 있습니다.", symbol)
        return data

    def get_intraday_history(self, symbol: str, period: str = "5d", interval: str = "1m") -> pd.DataFrame:
        logger.debug("[데이터] %s 분봉 다운로드 (period=%s, interval=%s)", symbol, period, interval)
        try:
            data = self._download(symbol, period=period, interval=interval, progress=False)
        except MarketDataDownloadError as exc:
            logger.error("[데이터] %s 분봉 다운로드 실패: %s", symbol, exc)
            return pd.DataFrame()
        if data.empty:
            logger.warning("[데이터] %s 분봉 데이터가 비어 있습니다.", symbol)
        return data

    def get_average_volume(self, symbol: str, window: int) -> float:
        history = self.get_daily_history(symbol, lookback_days=max(window * 2, 60))
        if history.empty:
            return 0.0
        return float(history["Volume"].tail(window).mean())

    def get_sector_performance(self, lookback_weeks: int) -> pd.DataFrame:
        # yfinance는 국내 섹터 지수를 직접 제공하지 않으므로, 예시로 S&P 섹터 ETF 사용
        sector_symbols = [
            "XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY",
        ]
        result = []
        for symbol in sector_symbols:
            try:
                data = self._download(symbol, period=f"{lookback_weeks}wk", interval="1d", progress=False)
            except MarketDataDownloadError as exc:
                logger.error("[스크리너] 섹터 %s 데이터 수신 실패: %s", symbol, exc)
                continue
            if len(data) < 2:
                continue
            start_price = data["Close"].iloc[0]
            end_price = data["Close"].iloc[-1]
            relative_return = (end_price / start_price) - 1
            result.append({"symbol": symbol, "return": relative_return})
        return pd.DataFrame(result)

    def get_fundamentals(self, symbol: str) -> FundamentalSnapshot:
        ticker = self._yf.Ticker(symbol)
        info = ticker.info or {}
        return FundamentalSnapshot(
            symbol=symbol,
            debt_to_equity=float(info.get("debtToEquity", 0) or 0) / 100 if info.get("debtToEquity") else 0,
            current_ratio=float(info.get("currentRatio", 0) or 0),
            cash_to_operating_expense_months=float(info.get("freeCashflow", 0) or 0) / max(
                float(info.get("operatingCashflow", 1) or 1),
                1,
            ) * 12,
            revenue_growth=float(info.get("revenueGrowth", 0) or 0),
            eps_growth=float(info.get("earningsQuarterlyGrowth", 0) or 0),
        )

    def get_recent_events(self, symbol: str) -> List[CorporateEvent]:
        ticker = self._yf.Ticker(symbol)
        events: List[CorporateEvent] = []
        try:
            calendar = ticker.calendar.T
        except Exception as exc:  # pragma: no cover - 외부 데이터 의존
            logger.debug("[데이터] %s 이벤트 조회 실패: %s", symbol, exc)
            return []

        for event_type, row in calendar.iterrows():
            date_value = row.get("Value")
            if isinstance(date_value, pd.Timestamp):
                events.append(
                    CorporateEvent(
                        symbol=symbol,
                        event_type=str(event_type).lower(),
                        timestamp=date_value.to_pydatetime(),
                        headline=f"{symbol} {event_type}",
                    )
                )
        return events

    def stream_quotes(self, symbols: Iterable[str], interval: str = "1m") -> Iterable[pd.DataFrame]:
        # yfinance는 스트리밍을 지원하지 않으므로, 폴링 방식으로 구현
        logger.info("[데이터] yfinance 폴링 기반 실시간 스트림 시작: %s", list(symbols))
        while True:
            snapshot = []
            for symbol in symbols:
                try:
                    df = self.get_intraday_history(symbol, period="1d", interval=interval)
                except MarketDataDownloadError as exc:
                    logger.error("[데이터] %s 실시간 스냅샷 실패: %s", symbol, exc)
                    continue
                if not df.empty:
                    last = df.tail(1).copy()
                    last["symbol"] = symbol
                    snapshot.append(last)
            if snapshot:
                yield pd.concat(snapshot)
            else:  # pragma: no cover - 네트워크 미가용 시
                logger.warning("[데이터] 실시간 스냅샷이 비었습니다. 잠시 후 재시도합니다.")
            # 외부에서 제어하도록 호출 측에서 sleep 처리

    def _download(self, symbol: str, **kwargs) -> pd.DataFrame:
        """yfinance 다운로드 헬퍼 (재시도 & 인증서 오류 처리)."""

        kwargs.setdefault("progress", False)
        kwargs.setdefault("auto_adjust", False)

        last_exception: Optional[Exception] = None
        for attempt in range(1, self._max_retries + 1):
            try:
                data = self._yf.download(symbol, session=self._session, **kwargs)
                if isinstance(data, dict):  # pragma: no cover - 다중 티커 반환 방지
                    return pd.DataFrame()
                return data
            except Exception as exc:  # pragma: no cover - 네트워크 실패 분기
                last_exception = exc
                if self._is_certificate_error(exc):
                    message = (
                        "SSL 인증서 검증에 실패했습니다. Windows 환경이라면 `Install Certificates.command` "
                        "실행 또는 시스템 프록시 설정을 확인해 주세요."
                    )
                    raise MarketDataDownloadError(message) from exc

                if attempt >= self._max_retries:
                    break

                logger.warning(
                    "[데이터] %s 다운로드 실패(%d/%d): %s", symbol, attempt, self._max_retries, exc
                )
                time.sleep(self._retry_backoff * attempt)

        raise MarketDataDownloadError(str(last_exception))

    @staticmethod
    def _is_certificate_error(exc: Exception) -> bool:
        """SSL 인증서 오류 여부를 판별."""

        certificate_errors = (
            RequestsSSLError if isinstance(RequestsSSLError, tuple) else (RequestsSSLError,)
        )
        urllib_errors = (
            Urllib3SSLError if isinstance(Urllib3SSLError, tuple) else (Urllib3SSLError,)
        )

        if isinstance(exc, (*certificate_errors, *urllib_errors)):
            return True

        message = str(exc).lower()
        return "certificate" in message and "verify" in message


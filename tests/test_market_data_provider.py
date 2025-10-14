"""YFinanceDataProvider 관련 단위 테스트."""

from __future__ import annotations

import os
import logging
from pathlib import Path

import pandas as pd
from requests.exceptions import SSLError

from data.market_data_provider import YFinanceDataProvider


class _DummyTicker:
    """yfinance.Ticker를 흉내 내는 단순 스텁."""

    def __init__(self) -> None:
        self.info = {}
        self.calendar = pd.DataFrame()


class _DummyYF:
    """yfinance 모듈을 대체하기 위한 테스트 스텁."""

    def __init__(self) -> None:
        self.calls = []

    def download(self, symbol, session=None, **kwargs):  # noqa: D401 - yfinance 대체 스텁
        """더미 다운로드 함수."""
        self.calls.append((symbol, kwargs))
        return pd.DataFrame({"Close": [1.0], "Volume": [100]})

    def Ticker(self, symbol):  # noqa: N802 - yfinance API 호환
        return _DummyTicker()


class _FailingCertYF:
    """SSL 인증서 오류를 일으키는 yfinance 대체 스텁."""

    def download(self, symbol, session=None, **kwargs):  # noqa: D401 - yfinance 대체 스텁
        raise SSLError("SSL 인증서 검증에 실패했습니다.")

    def Ticker(self, symbol):  # pragma: no cover - 본 테스트에서는 사용하지 않음
        return _DummyTicker()


def test_download_sets_auto_adjust_flag(tmp_path):
    """_download 호출 시 auto_adjust=False가 전달되는지 확인."""

    cert_dir = tmp_path / "certs"
    cert_dir.mkdir()
    cert_path = cert_dir / "cacert.pem"
    cert_path.write_text("dummy")

    dummy_yf = _DummyYF()
    provider = YFinanceDataProvider(
        verify=True,
        cert_path=str(cert_path),
        yf_module=dummy_yf,
        suppress_yf_warnings=False,
    )

    df = provider._download("TEST")
    assert not df.empty
    assert dummy_yf.calls, "yfinance download 호출이 수행되어야 합니다."
    _, kwargs = dummy_yf.calls[0]
    assert kwargs.get("auto_adjust") is False


def test_certificate_auto_copy_creates_ascii_path(tmp_path, monkeypatch):
    """auto_copy_cert 설정 시 비ASCII 경로를 안전한 경로로 복사하는지 확인."""

    non_ascii_dir = tmp_path / "한글경로"
    non_ascii_dir.mkdir()
    source_cert = non_ascii_dir / "cacert.pem"
    source_cert.write_text("dummy")

    monkeypatch.setenv("SSL_CERT_FILE", "", prepend=False)
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", "", prepend=False)

    provider = YFinanceDataProvider(
        verify=True,
        cert_path=str(source_cert),
        auto_copy_cert=True,
        yf_module=_DummyYF(),
        suppress_yf_warnings=False,
    )

    verify_path = provider._session.verify
    assert isinstance(verify_path, str)
    assert os.path.exists(verify_path)
    assert all(ord(ch) < 128 for ch in verify_path)
    assert os.environ.get("SSL_CERT_FILE") == verify_path
    assert os.environ.get("REQUESTS_CA_BUNDLE") == verify_path

    cert_file = Path(verify_path)
    if cert_file.exists():
        cert_file.unlink()
        parent = cert_file.parent
        if parent.exists() and not any(parent.iterdir()):
            parent.rmdir()


def test_certificate_failures_downgrade_logging(caplog):
    """동일한 인증서 오류가 반복될 때 에러 로그가 중복되지 않는지 확인."""

    provider = YFinanceDataProvider(
        max_retries=1,
        yf_module=_FailingCertYF(),
        suppress_yf_warnings=False,
    )

    with caplog.at_level(logging.INFO):
        provider.get_daily_history("AAA", lookback_days=5)
        provider.get_daily_history("BBB", lookback_days=5)

    ssl_error_logs = [record for record in caplog.records if "SSL 인증서 오류 감지" in record.message]
    assert len(ssl_error_logs) == 1, "SSL 인증서 오류 로그는 최초 한 번만 ERROR로 기록되어야 합니다."

    info_logs = [
        record
        for record in caplog.records
        if record.levelno == logging.INFO and "일봉 실패" in record.message
    ]
    assert len(info_logs) == 1, "중복되는 인증서 실패 로그는 INFO 한 번만 출력되어야 합니다."

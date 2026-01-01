from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..config import KISConfig


PROD_BASE = "https://openapi.koreainvestment.com:9443"
VTS_BASE = "https://openapivts.koreainvestment.com:29443"

SECRETS_PATH = Path("v2/config/secrets.json")
TOKEN_CACHE_PATH = Path("v2/config/token_cache.json")
WS_CACHE_PATH = Path("v2/config/ws_key_cache.json")


@dataclass(frozen=True)
class TokenInfo:
    token: str
    expires_at: float


class TokenError(RuntimeError):
    pass


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
    tmp.replace(path)


def load_secrets(path: Path = SECRETS_PATH) -> Dict[str, Any]:
    return _read_json(path)


def _resolve_base_url(kis: KISConfig) -> str:
    if kis.base_url:
        return kis.base_url
    env = kis.env.lower()
    if env in {"vts", "paper", "sandbox", "test"}:
        return VTS_BASE
    return PROD_BASE


def _post_form(url: str, data: Dict[str, Any]) -> Dict[str, Any]:
    body = urlencode(data).encode("utf-8")
    req = Request(url, data=body, headers={"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"})
    with urlopen(req, timeout=10) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def _post_json(url: str, data: Dict[str, Any]) -> Dict[str, Any]:
    body = json.dumps(data).encode("utf-8")
    req = Request(url, data=body, headers={"Content-Type": "application/json; charset=UTF-8"})
    with urlopen(req, timeout=10) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def _cached_token(path: Path) -> Optional[TokenInfo]:
    cached = _read_json(path)
    token = cached.get("token")
    expires_at = cached.get("expires_at")
    if not token or not expires_at:
        return None
    if time.time() >= float(expires_at):
        return None
    return TokenInfo(token=token, expires_at=float(expires_at))


def _save_token(path: Path, token: str, expires_in: float, skew_seconds: int = 60) -> TokenInfo:
    expires_at = time.time() + float(expires_in) - skew_seconds
    info = {"token": token, "expires_at": expires_at, "issued_at": time.time()}
    _write_json(path, info)
    return TokenInfo(token=token, expires_at=expires_at)


def get_access_token(kis: KISConfig, force_refresh: bool = False) -> str:
    if not force_refresh:
        cached = _cached_token(TOKEN_CACHE_PATH)
        if cached:
            return cached.token

    secrets = load_secrets()
    app_key = secrets.get("APP_KEY") or kis.app_key
    app_secret = secrets.get("APP_SECRET") or kis.app_secret
    if not app_key or not app_secret:
        raise TokenError("Missing APP_KEY/APP_SECRET in secrets.json or config")

    base = _resolve_base_url(kis)
    url = f"{base}/oauth2/tokenP"
    payload = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "appsecret": app_secret,
    }
    resp = _post_form(url, payload)
    token = resp.get("access_token")
    expires_in = resp.get("expires_in", 0)
    if not token:
        raise TokenError(f"Failed to fetch access_token: {resp}")
    return _save_token(TOKEN_CACHE_PATH, token, expires_in).token


def get_approval_key(kis: KISConfig, force_refresh: bool = False) -> str:
    if not force_refresh:
        cached = _cached_token(WS_CACHE_PATH)
        if cached:
            return cached.token

    secrets = load_secrets()
    app_key = secrets.get("APP_KEY") or kis.app_key
    app_secret = secrets.get("APP_SECRET") or kis.app_secret
    if not app_key or not app_secret:
        raise TokenError("Missing APP_KEY/APP_SECRET in secrets.json or config")

    base = _resolve_base_url(kis)
    url = f"{base}/oauth2/approval"
    payload = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "appsecret": app_secret,
        "secretkey": app_secret,
    }
    resp = _post_json(url, payload)
    key = resp.get("approval_key")
    if not key:
        raise TokenError(f"Failed to fetch approval_key: {resp}")
    # Approval key does not always return TTL; default to 12 hours.
    return _save_token(WS_CACHE_PATH, key, expires_in=60 * 60 * 12, skew_seconds=60).token

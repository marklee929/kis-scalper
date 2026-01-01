from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:  # pragma: no cover - optional dependency
    yaml = None


DEFAULT_CONFIG_PATH = Path("v2/config/config.yaml")


@dataclass(frozen=True)
class KISConfig:
    env: str
    base_url: str
    app_key: str
    app_secret: str
    account_no: str
    custtype: str
    tr_id: str


@dataclass(frozen=True)
class WebSocketConfig:
    url: str
    ping_interval: int
    reconnect_min_delay: int
    reconnect_max_delay: int
    mock: bool
    mock_tick_interval: float


@dataclass(frozen=True)
class DataConfig:
    bar_1s_window: int
    bar_1m_window: int
    feature_window_short: int
    feature_window_long: int


@dataclass(frozen=True)
class LoggingConfig:
    logs_dir: str
    transition_prefix: str
    summary_prefix: str


@dataclass(frozen=True)
class TradingConfig:
    starting_cash: float
    fee_rate: float
    slippage_rate: float
    max_position_size: float
    cooldown_seconds: int
    max_spread_ratio: float


@dataclass(frozen=True)
class ModelConfig:
    update_interval_seconds: int
    action_size: float


@dataclass(frozen=True)
class AppConfig:
    kis: KISConfig
    websocket: WebSocketConfig
    data: DataConfig
    logging: LoggingConfig
    trading: TradingConfig
    model: ModelConfig
    symbols: List[str]


class ConfigError(RuntimeError):
    pass


def _read_yaml(path: Path) -> Dict[str, Any]:
    if yaml is None:
        raise ConfigError("PyYAML is required to read config.yaml")
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ConfigError("Invalid config format")
    return data


def load_config(path: Path | str = DEFAULT_CONFIG_PATH) -> AppConfig:
    path = Path(path)
    raw = _read_yaml(path)

    kis = raw.get("kis", {})
    ws = raw.get("websocket", {})
    data = raw.get("data", {})
    logging = raw.get("logging", {})
    trading = raw.get("trading", {})
    model = raw.get("model", {})

    return AppConfig(
        kis=KISConfig(
            env=str(kis.get("env", "vts")),
            base_url=str(kis.get("base_url", "")),
            app_key=str(kis.get("app_key", "")),
            app_secret=str(kis.get("app_secret", "")),
            account_no=str(kis.get("account_no", "")),
            custtype=str(kis.get("custtype", "P")),
            tr_id=str(kis.get("tr_id", "H0STCNT0")),
        ),
        websocket=WebSocketConfig(
            url=str(ws.get("url", "")),
            ping_interval=int(ws.get("ping_interval", 25)),
            reconnect_min_delay=int(ws.get("reconnect_min_delay", 5)),
            reconnect_max_delay=int(ws.get("reconnect_max_delay", 300)),
            mock=bool(ws.get("mock", False)),
            mock_tick_interval=float(ws.get("mock_tick_interval", 0.2)),
        ),
        data=DataConfig(
            bar_1s_window=int(data.get("bar_1s_window", 120)),
            bar_1m_window=int(data.get("bar_1m_window", 120)),
            feature_window_short=int(data.get("feature_window_short", 30)),
            feature_window_long=int(data.get("feature_window_long", 60)),
        ),
        logging=LoggingConfig(
            logs_dir=str(logging.get("logs_dir", "v2/logs")),
            transition_prefix=str(logging.get("transition_prefix", "transition")),
            summary_prefix=str(logging.get("summary_prefix", "summary")),
        ),
        trading=TradingConfig(
            starting_cash=float(trading.get("starting_cash", 10_000_000)),
            fee_rate=float(trading.get("fee_rate", 0.00015)),
            slippage_rate=float(trading.get("slippage_rate", 0.0005)),
            max_position_size=float(trading.get("max_position_size", 100)),
            cooldown_seconds=int(trading.get("cooldown_seconds", 1)),
            max_spread_ratio=float(trading.get("max_spread_ratio", 0.003)),
        ),
        model=ModelConfig(
            update_interval_seconds=int(model.get("update_interval_seconds", 1)),
            action_size=float(model.get("action_size", 1)),
        ),
        symbols=[str(s) for s in raw.get("symbols", [])],
    )

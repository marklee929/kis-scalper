from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any, Dict, Optional

from ..schemas import TickEvent


def normalize_symbol(symbol: str) -> str:
    s = str(symbol).strip().upper()
    s = s.replace("-", "").replace(".", "").lstrip("A")
    if s.isdigit() and len(s) <= 6:
        s = s.zfill(6)
    return f"A{s}"


def _parse_timestamp(date_str: str, time_str: str) -> int:
    if not date_str or not time_str:
        return int(time.time() * 1000)
    try:
        dt = datetime.strptime(f"{date_str}{time_str}", "%Y%m%d%H%M%S")
        return int(dt.timestamp() * 1000)
    except ValueError:
        return int(time.time() * 1000)


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _from_json(message: Dict[str, Any]) -> Optional[TickEvent]:
    header = message.get("header", {})
    body = message.get("body", {})
    tr_id = header.get("tr_id") or body.get("tr_id")
    if tr_id != "H0STCNT0":
        return None
    output = body.get("output") or {}
    symbol = normalize_symbol(output.get("MKSC_SHRN_ISCD", ""))
    if not symbol:
        return None
    ts = _parse_timestamp(output.get("BSOP_DATE", ""), output.get("STCK_CNTG_HOUR", ""))
    return TickEvent(
        timestamp_ms=ts,
        symbol=symbol,
        last_price=_safe_float(output.get("STCK_PRPR")),
        volume=_safe_float(output.get("CNTG_VOL")),
        bid_price=_safe_float(output.get("BIDP1")),
        ask_price=_safe_float(output.get("ASKP1")),
        bid_size=_safe_float(output.get("BIDP_RSQN1")),
        ask_size=_safe_float(output.get("ASKP_RSQN1")),
        raw=output,
    )


def _from_pipe(message: str) -> Optional[TickEvent]:
    parts = message.split("|")
    if len(parts) < 4:
        return None
    tr_id = parts[1]
    if tr_id != "H0STCNT0":
        return None
    payload = parts[3]
    fields = payload.split("^")
    if len(fields) < 15:
        return None
    symbol = normalize_symbol(fields[0])
    if not symbol:
        return None
    exec_time = fields[1]
    price = _safe_float(fields[2])
    ask_price = _safe_float(fields[10]) if len(fields) > 10 else 0.0
    bid_price = _safe_float(fields[11]) if len(fields) > 11 else 0.0
    volume = _safe_float(fields[12]) if len(fields) > 12 else 0.0
    ask_size = _safe_float(fields[36]) if len(fields) > 36 else 0.0
    bid_size = _safe_float(fields[37]) if len(fields) > 37 else 0.0
    trade_date = fields[33] if len(fields) > 33 else ""
    ts = _parse_timestamp(trade_date, exec_time)
    return TickEvent(
        timestamp_ms=ts,
        symbol=symbol,
        last_price=price,
        volume=volume,
        bid_price=bid_price,
        ask_price=ask_price,
        bid_size=bid_size,
        ask_size=ask_size,
        raw=None,
    )


def parse_message(message: Any) -> Optional[TickEvent]:
    if message is None:
        return None
    if isinstance(message, TickEvent):
        return message
    if isinstance(message, dict):
        return _from_json(message)
    if isinstance(message, str):
        msg = message.strip()
        if not msg:
            return None
        if msg.startswith("{"):
            try:
                return _from_json(json.loads(msg))
            except json.JSONDecodeError:
                return None
        if msg[0] in {"0", "1"}:
            return _from_pipe(msg)
    return None

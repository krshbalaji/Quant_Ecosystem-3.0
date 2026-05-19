from __future__ import annotations

from enum import Enum
from typing import Any, Dict

from quant_ecosystem.contracts.position import Position


class HealthState(str, Enum):
    HEALTHY = "HEALTHY"
    WEAK = "WEAK"
    RECOVERY = "RECOVERY"
    BREAKOUT = "BREAKOUT"
    DISTRIBUTION = "DISTRIBUTION"
    DEAD_MONEY = "DEAD_MONEY"
    HIGH_CONVICTION = "HIGH_CONVICTION"
    EXIT_RISK = "EXIT_RISK"


def _to_position(position: Any) -> Position:
    if isinstance(position, Position):
        return position
    if isinstance(position, dict):
        return Position.from_mapping(position)
    raise TypeError("position must be a Position or dict mapping")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def assess_position_health(
    position: Any,
    trend_proxy: float = 0.0,
    confidence_decay: float = 0.0,
) -> HealthState:
    position = _to_position(position)
    trend_proxy = max(0.0, min(1.0, _safe_float(trend_proxy)))
    confidence_decay = max(0.0, min(1.0, _safe_float(confidence_decay)))

    qty = int(position.qty)
    avg_entry = float(position.avg_entry)
    notional_base = max(1.0, abs(qty) * max(abs(avg_entry), 1.0))
    pnl_pct = float(position.pnl_unrealized) / notional_base
    holding_days = max(0.0, _safe_float(position.metadata.get("holding_days", 0.0)))
    conviction = max(0.0, min(1.0, _safe_float(position.thesis.get("confidence", 0.0))))
    intact = bool(position.thesis.get("intact", True))
    distribution_signal = bool(
        position.thesis.get("distribution_signal") or position.metadata.get("distribution_signal")
    )
    exit_signal = bool(
        position.thesis.get("exit_signal") or position.metadata.get("exit_signal")
    )

    if qty == 0 or str(position.lifecycle).upper() == "RETIRED":
        return HealthState.DEAD_MONEY

    if exit_signal or (not intact and pnl_pct <= 0.0):
        return HealthState.EXIT_RISK

    if pnl_pct <= -0.05 and holding_days >= 14:
        return HealthState.DEAD_MONEY

    if distribution_signal or (pnl_pct >= 0.03 and trend_proxy < 0.25 and holding_days >= 14):
        return HealthState.DISTRIBUTION

    if pnl_pct >= 0.05 and trend_proxy >= 0.45:
        return HealthState.BREAKOUT

    if pnl_pct >= 0.02 and trend_proxy >= 0.35:
        return HealthState.HEALTHY

    if pnl_pct >= 0.0 and conviction >= 0.65 and trend_proxy >= 0.4:
        return HealthState.HIGH_CONVICTION

    if pnl_pct < 0.0 and intact and trend_proxy >= 0.3:
        return HealthState.RECOVERY

    if pnl_pct < -0.02 and holding_days >= 7:
        return HealthState.EXIT_RISK

    if abs(pnl_pct) <= 0.02 and holding_days >= 21 and trend_proxy < 0.3:
        return HealthState.WEAK

    return HealthState.WEAK

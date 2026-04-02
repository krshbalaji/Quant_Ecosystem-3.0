from __future__ import annotations

from typing import Any, Dict


def explain_trade(signal: Dict[str, Any], regime: str | None = None, market_bias: str | None = None) -> str:
    signal = dict(signal or {})
    symbol = str(signal.get("symbol", "UNKNOWN"))
    strategy = str(signal.get("strategy_id", signal.get("strategy", "strategy")))
    side = str(signal.get("side", "BUY")).upper()
    confidence = round(float(signal.get("confidence", 0.0) or 0.0), 2)
    regime_name = str(regime or signal.get("regime", "RANGE")).upper()
    bias = str(market_bias or signal.get("market_bias", "NEUTRAL")).upper()
    return (
        f"Trade {side} {symbol} because {strategy} aligned with {regime_name} "
        f"under {bias} bias at confidence {confidence}."
    )

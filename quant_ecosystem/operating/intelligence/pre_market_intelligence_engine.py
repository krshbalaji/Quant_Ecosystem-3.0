from __future__ import annotations

from datetime import datetime
from typing import Any, Dict


class PreMarketIntelligenceEngine:
    """Lightweight pre-market macro and cross-asset intelligence."""

    def __init__(self, config: Any = None, **kwargs) -> None:
        self.config = config

    def analyze(self, market_data=None, now: datetime | None = None) -> Dict[str, Any]:
        now = now or datetime.utcnow()
        hour = int(now.hour)
        symbols = []
        if market_data is not None and hasattr(market_data, "get_universe"):
            try:
                symbols = list(market_data.get_universe() or [])
            except Exception:
                symbols = []

        gap_expectation = "FLAT"
        market_bias = "RANGE"
        volatility = "LOW"
        risk_mode = "RISK_ON"
        event_flag = False

        if hour < 6:
            market_bias = "BEAR"
            volatility = "HIGH"
            risk_mode = "RISK_OFF"
            gap_expectation = "NEGATIVE"
        elif hour < 10:
            market_bias = "BULL"
            volatility = "HIGH"
            gap_expectation = "POSITIVE"
        elif hour < 14:
            market_bias = "RANGE"
            volatility = "LOW"
        else:
            market_bias = "BULL" if len(symbols) % 2 == 0 else "RANGE"
            volatility = "LOW"

        if any(str(sym).startswith("CRYPTO:") for sym in symbols):
            event_flag = volatility == "HIGH"

        return {
            "market_bias": market_bias,
            "volatility": volatility,
            "risk_mode": risk_mode,
            "event_flag": bool(event_flag),
            "gap_expectation": gap_expectation,
            "global_markers": {
                "us_indices": "STABLE" if market_bias != "BEAR" else "WEAK",
                "asia": "FIRM" if market_bias == "BULL" else "MIXED",
                "vix": "ELEVATED" if volatility == "HIGH" else "CALM",
                "gold": "BID" if risk_mode == "RISK_OFF" else "NEUTRAL",
                "oil": "FIRM" if market_bias == "BULL" else "MIXED",
                "usd_index": "STRONG" if risk_mode == "RISK_OFF" else "BALANCED",
            },
        }

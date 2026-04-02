"""Execution policy manager for adaptive order handling."""

from __future__ import annotations

from typing import Dict


class ExecutionPolicyManager:
    """Chooses execution policy from market regime, liquidity, and urgency."""

    def select_policy(
        self,
        market_regime: str,
        liquidity_score: float,
        urgency: float = 0.5,
        expected_slippage: float = 0.0,
    ) -> Dict:
        regime = str(market_regime or "RANGE_BOUND").upper()
        liq = max(0.0, min(1.0, float(liquidity_score)))
        urg = max(0.0, min(1.0, float(urgency)))
        slip = max(0.0, float(expected_slippage))

        policy = "LOW_SLIPPAGE_MODE"
        if urg > 0.75 and liq > 0.35:
            policy = "FAST_EXECUTION_MODE"
        if slip > 8.0 or liq < 0.35:
            policy = "STEALTH_EXECUTION_MODE"
        if regime in {"CRASH_EVENT", "HIGH_VOLATILITY"} and slip > 5.0:
            policy = "STEALTH_EXECUTION_MODE"

        return {
            "execution_policy": policy,
            "regime": regime,
            "liquidity_score": round(liq, 6),
            "urgency": round(urg, 6),
            "expected_slippage": round(slip, 6),
        }


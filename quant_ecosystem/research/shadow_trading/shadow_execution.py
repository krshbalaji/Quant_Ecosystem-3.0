"""Shadow execution simulator using live prices."""

from __future__ import annotations

from typing import Dict


class ShadowExecution:
    """Simulates entry/exit fills with slippage and fees."""

    def __init__(self, fee_bps: float = 2.5, base_slippage_bps: float = 1.5, **kwargs):
        self.fee_bps = float(fee_bps)
        self.base_slippage_bps = float(base_slippage_bps)

    def simulate_fill(self, signal: Dict) -> Dict:
        side = str(signal.get("side", "BUY")).upper()
        price = self._f(signal.get("price", 0.0))
        qty = int(signal.get("qty", 1) or 1)
        volatility = max(0.01, self._f(signal.get("volatility", 0.1)))
        spread_bps = max(0.0, self._f(signal.get("spread_bps", 0.0)))
        slip_bps = self.base_slippage_bps * (1.0 + (volatility * 0.8)) + (spread_bps * 0.15)

        if side == "BUY":
            fill_price = price * (1.0 + slip_bps / 10000.0)
        else:
            fill_price = price * (1.0 - slip_bps / 10000.0)

        notional = fill_price * qty
        fee = notional * (self.fee_bps / 10000.0)
        return {
            "symbol": str(signal.get("symbol", "")),
            "strategy_id": str(signal.get("strategy_id", "")),
            "side": side,
            "qty": qty,
            "entry_price": round(fill_price, 8),
            "exit_price": round(fill_price, 8),
            "fee": round(fee, 8),
            "slippage_bps": round(slip_bps, 8),
            "regime": str(signal.get("regime", "UNKNOWN")).upper(),
        }

    def _f(self, value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0


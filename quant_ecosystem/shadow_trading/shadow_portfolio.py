"""Shadow portfolio state for simulated positions/PnL/exposure."""

from __future__ import annotations

from typing import Dict


class ShadowPortfolio:
    """Maintains simulated capital and shadow positions."""

    def __init__(self, initial_capital: float = 100000.0, **kwargs):
        self.initial_capital = float(initial_capital)
        self.cash = float(initial_capital)
        self.equity = float(initial_capital)
        self.positions: Dict[str, Dict] = {}
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0

    def apply_fill(self, fill: Dict, mark_price: float) -> Dict:
        symbol = str(fill.get("symbol", ""))
        side = str(fill.get("side", "BUY")).upper()
        qty = int(fill.get("qty", 0) or 0)
        price = self._f(fill.get("entry_price", 0.0))
        fee = self._f(fill.get("fee", 0.0))
        if qty <= 0 or price <= 0:
            return {"realized_pnl": 0.0}

        pos = self.positions.get(symbol, {"qty": 0, "avg_price": 0.0, "side": side})
        realized = 0.0
        if pos["qty"] == 0:
            pos = {"qty": qty, "avg_price": price, "side": side}
        elif pos["side"] == side:
            new_qty = pos["qty"] + qty
            pos["avg_price"] = ((pos["avg_price"] * pos["qty"]) + (price * qty)) / max(1, new_qty)
            pos["qty"] = new_qty
        else:
            close_qty = min(pos["qty"], qty)
            if pos["side"] == "BUY":
                realized += (price - pos["avg_price"]) * close_qty
            else:
                realized += (pos["avg_price"] - price) * close_qty
            pos["qty"] -= close_qty
            if pos["qty"] == 0 and qty > close_qty:
                pos = {"qty": qty - close_qty, "avg_price": price, "side": side}
            elif pos["qty"] == 0:
                pos = {"qty": 0, "avg_price": 0.0, "side": side}

        realized -= fee
        self.realized_pnl += realized
        self.cash += realized
        if pos["qty"] <= 0:
            self.positions.pop(symbol, None)
        else:
            self.positions[symbol] = pos
        self.mark_to_market({symbol: mark_price})
        return {"realized_pnl": round(realized, 8)}

    def mark_to_market(self, latest_prices: Dict[str, float]) -> None:
        unrealized = 0.0
        for symbol, pos in self.positions.items():
            px = self._f(latest_prices.get(symbol, pos.get("avg_price", 0.0)))
            if pos["side"] == "BUY":
                unrealized += (px - pos["avg_price"]) * pos["qty"]
            else:
                unrealized += (pos["avg_price"] - px) * pos["qty"]
        self.unrealized_pnl = unrealized
        self.equity = self.initial_capital + self.realized_pnl + self.unrealized_pnl

    def exposure_pct(self) -> float:
        if self.equity <= 0:
            return 0.0
        notional = sum(abs(v["avg_price"] * v["qty"]) for v in self.positions.values())
        return (notional / self.equity) * 100.0

    def _f(self, value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0


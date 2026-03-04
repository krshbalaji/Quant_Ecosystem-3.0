"""Trade feedback collector for adaptive learning."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, List, Optional


class TradeFeedbackCollector:
    """Normalizes live trade outcomes into learning-ready feedback rows."""

    REQUIRED_KEYS = (
        "symbol",
        "strategy_id",
        "entry_price",
        "exit_price",
        "pnl",
        "execution_slippage",
        "regime",
        "volatility",
        "timestamp",
    )

    def collect_trade(self, trade: Dict, defaults: Optional[Dict] = None) -> Dict:
        """Collect and normalize one trade feedback item."""
        payload = dict(defaults or {})
        payload.update(dict(trade or {}))

        entry = self._f(payload.get("entry_price", payload.get("price", 0.0)))
        exit_px = self._f(payload.get("exit_price", payload.get("mark_price", entry)))
        side = str(payload.get("side", "BUY")).upper()
        qty = max(0.0, self._f(payload.get("qty", payload.get("quantity", 0.0))))
        pnl = self._f(payload.get("pnl", payload.get("realized_pnl", 0.0)))
        if abs(pnl) <= 1e-12 and entry > 0 and exit_px > 0 and qty > 0:
            if side == "BUY":
                pnl = (exit_px - entry) * qty
            else:
                pnl = (entry - exit_px) * qty

        slip = self._f(payload.get("execution_slippage", payload.get("slippage_bps", 0.0)))
        ts = payload.get("timestamp")
        if not ts:
            ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        return {
            "symbol": str(payload.get("symbol", "")).strip(),
            "strategy_id": str(payload.get("strategy_id", payload.get("strategy", ""))).strip(),
            "entry_price": round(entry, 8),
            "exit_price": round(exit_px, 8),
            "pnl": round(pnl, 8),
            "execution_slippage": round(slip, 8),
            "regime": str(payload.get("regime", "UNKNOWN")).upper(),
            "volatility": round(self._f(payload.get("volatility", 0.0)), 8),
            "timestamp": str(ts),
            "side": side,
            "qty": qty,
        }

    def collect_batch(self, trades: Iterable[Dict], defaults: Optional[Dict] = None) -> List[Dict]:
        out = []
        for item in trades or []:
            row = self.collect_trade(item, defaults=defaults)
            if row.get("strategy_id") and row.get("symbol"):
                out.append(row)
        return out

    def _f(self, value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0


"""
PATCH: quant_ecosystem/allocation/allocation_engine.py
FIX:   Constructor now accepts config=None, **kwargs.
"""


class AllocationEngine:
    """
    Computes capital allocation weights across strategies/assets.
    """

    def __init__(self, config=None, **kwargs):
        self.config = config

    def allocate(self, signals: dict) -> dict:
        """Return weight map from signals (stub — equal weight)."""
        if not signals:
            return {}
        weight = 1.0 / len(signals)
        return {k: weight for k in signals}

    def rebalance(self, regime=None, strategy_rows=None, capital_available_pct=100.0, current_drawdown_pct=0.0, signals=None) -> dict:
        rows = list(strategy_rows or signals or [])
        if not rows:
            return {"allocation": {}, "rebalanced": False, "regime": regime or "UNKNOWN"}
        weight = float(capital_available_pct or 100.0) / max(len(rows), 1)
        allocation = {}
        for row in rows:
            if isinstance(row, dict):
                key = str(row.get("id") or row.get("strategy_id") or row.get("strategy") or row.get("symbol") or "UNKNOWN")
            else:
                key = str(row)
            allocation[key] = round(weight, 2)
        return {
            "allocation": allocation,
            "rebalanced": True,
            "regime": regime or "UNKNOWN",
            "drawdown_pct": float(current_drawdown_pct or 0.0),
        }

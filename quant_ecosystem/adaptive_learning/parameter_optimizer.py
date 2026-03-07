"""Parameter optimizer for adaptive learning."""

from __future__ import annotations

from typing import Dict, List


class ParameterOptimizer:
    """Optimizes strategy parameters using rolling performance heuristics."""

    def __init__(self, min_trades: int = 30, **kwargs):
        self.min_trades = max(10, int(min_trades))

    def optimize(self, strategy_id: str, regime_rows: List[Dict], current_params: Dict | None = None) -> Dict:
        params = dict(current_params or {})
        if not regime_rows:
            return {"strategy_id": strategy_id, "parameter_updates": {}, "learning_score": 0.0}

        weighted_score = 0.0
        weight_sum = 0.0
        for row in regime_rows:
            trades = max(1, int(row.get("trades", 1)))
            w = min(1.0, trades / 200.0)
            sharpe = float(row.get("sharpe", 0.0))
            win_rate = float(row.get("win_rate", 0.0)) / 100.0
            avg_pnl = float(row.get("avg_pnl", 0.0))
            weighted_score += ((0.5 * sharpe) + (0.3 * win_rate) + (0.2 * avg_pnl)) * w
            weight_sum += w
        learning_score = weighted_score / max(1e-9, weight_sum)

        updates = {}
        # Heuristic parameter adaptation.
        rsi_thr = int(params.get("rsi_threshold", 70))
        ema_fast = int(params.get("ema_fast", 9))
        ema_slow = int(params.get("ema_slow", 21))
        atr_mult = float(params.get("atr_stop_multiplier", 1.8))
        risk_alloc = float(params.get("risk_allocation", 1.0))

        if learning_score < 0.0:
            updates["rsi_threshold"] = max(55, rsi_thr - 2)
            updates["ema_fast"] = max(5, ema_fast - 1)
            updates["ema_slow"] = max(updates["ema_fast"] + 3, ema_slow - 2)
            updates["atr_stop_multiplier"] = round(min(3.0, atr_mult + 0.1), 4)
            updates["risk_allocation"] = round(max(0.25, risk_alloc * 0.9), 4)
        elif learning_score > 0.4:
            updates["rsi_threshold"] = min(80, rsi_thr + 1)
            updates["ema_fast"] = min(20, ema_fast + 1)
            updates["ema_slow"] = min(60, ema_slow + 1)
            updates["atr_stop_multiplier"] = round(max(1.0, atr_mult - 0.05), 4)
            updates["risk_allocation"] = round(min(2.0, risk_alloc * 1.05), 4)
        else:
            updates["risk_allocation"] = round(risk_alloc, 4)

        return {
            "strategy_id": strategy_id,
            "parameter_updates": updates,
            "learning_score": round(learning_score, 6),
        }


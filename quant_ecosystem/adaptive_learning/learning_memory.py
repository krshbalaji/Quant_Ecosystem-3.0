"""Persistent learning memory for adaptive updates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List


class LearningMemory:
    """Long-term performance memory store by strategy and regime."""

    def __init__(self, path: str = "quant_ecosystem/adaptive_learning/memory/learning_memory.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def add_feedback(self, feedback: Dict) -> None:
        sid = str(feedback.get("strategy_id", "")).strip()
        regime = str(feedback.get("regime", "UNKNOWN")).upper()
        if not sid:
            return

        node = self._data.setdefault("strategies", {}).setdefault(sid, {})
        reg = node.setdefault(
            regime,
            {
                "trades": 0,
                "wins": 0,
                "pnl_sum": 0.0,
                "pnl_sq_sum": 0.0,
                "slippage_sum": 0.0,
                "volatility_sum": 0.0,
                "recent_pnl": [],
                "recent_slippage": [],
            },
        )

        pnl = float(feedback.get("pnl", 0.0))
        slip = float(feedback.get("execution_slippage", 0.0))
        vol = float(feedback.get("volatility", 0.0))
        reg["trades"] += 1
        reg["wins"] += 1 if pnl > 0 else 0
        reg["pnl_sum"] += pnl
        reg["pnl_sq_sum"] += pnl * pnl
        reg["slippage_sum"] += slip
        reg["volatility_sum"] += vol
        reg["recent_pnl"] = (reg["recent_pnl"] + [pnl])[-400:]
        reg["recent_slippage"] = (reg["recent_slippage"] + [slip])[-400:]

    def summary(self) -> Dict:
        out = {"strategies": {}}
        for sid, by_regime in self._data.get("strategies", {}).items():
            out["strategies"][sid] = {}
            for regime, row in by_regime.items():
                trades = max(1, int(row.get("trades", 0)))
                pnl_sum = float(row.get("pnl_sum", 0.0))
                avg_pnl = pnl_sum / trades
                win_rate = (float(row.get("wins", 0)) / trades) * 100.0
                variance = (float(row.get("pnl_sq_sum", 0.0)) / trades) - (avg_pnl * avg_pnl)
                sharpe = 0.0
                if variance > 1e-12:
                    sharpe = avg_pnl / (variance**0.5)
                out["strategies"][sid][regime] = {
                    "avg_pnl": round(avg_pnl, 8),
                    "win_rate": round(win_rate, 6),
                    "sharpe": round(sharpe, 6),
                    "trades": int(row.get("trades", 0)),
                    "avg_slippage": round(float(row.get("slippage_sum", 0.0)) / trades, 8),
                    "avg_volatility": round(float(row.get("volatility_sum", 0.0)) / trades, 8),
                }
        return out

    def strategy_regime_rows(self) -> List[Dict]:
        rows = []
        summary = self.summary()
        for sid, regimes in summary.get("strategies", {}).items():
            for regime, metrics in regimes.items():
                rows.append({"strategy_id": sid, "regime": regime, **metrics})
        return rows

    def save(self) -> None:
        self.path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    def _load(self) -> Dict:
        if not self.path.exists():
            return {"strategies": {}}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                payload.setdefault("strategies", {})
                return payload
        except Exception:
            pass
        return {"strategies": {}}


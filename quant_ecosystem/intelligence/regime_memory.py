from __future__ import annotations

import json
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional

DEFAULT_MEMORY_PATH = "quant_ecosystem/intelligence/regime_memory.json"
DEFAULT_EXPECTED_DURATION = {
    "TRENDING_BULLISH": 8.0,
    "TRENDING_BEARISH": 8.0,
    "RANGE_BOUND": 6.0,
    "VOLATILE_BREAKOUT": 3.0,
    "MEAN_REVERSION": 5.0,
    "ACCUMULATION": 7.0,
    "DISTRIBUTION": 5.0,
    "LIQUIDITY_SWEEP": 4.0,
    "HIGH_VOLATILITY": 4.0,
    "CRASH_EVENT": 2.0,
    "UNKNOWN": 4.0,
}
DEFAULT_TRANSITION_PRIORS = {
    "TRENDING_BULLISH": {"DISTRIBUTION": 0.35, "VOLATILE_BREAKOUT": 0.20, "TRENDING_BULLISH": 0.20, "MEAN_REVERSION": 0.15},
    "TRENDING_BEARISH": {"DISTRIBUTION": 0.30, "VOLATILE_BREAKOUT": 0.20, "TRENDING_BEARISH": 0.20, "MEAN_REVERSION": 0.15},
    "ACCUMULATION": {"VOLATILE_BREAKOUT": 0.40, "RANGE_BOUND": 0.25, "TRENDING_BULLISH": 0.20, "DISTRIBUTION": 0.10},
    "DISTRIBUTION": {"MEAN_REVERSION": 0.30, "VOLATILE_BREAKOUT": 0.25, "TRENDING_BEARISH": 0.20, "RANGE_BOUND": 0.15},
    "HIGH_VOLATILITY": {"MEAN_REVERSION": 0.40, "VOLATILE_BREAKOUT": 0.20, "RANGE_BOUND": 0.15},
    "VOLATILE_BREAKOUT": {"MEAN_REVERSION": 0.45, "TRENDING_BULLISH": 0.25, "TRENDING_BEARISH": 0.10, "RANGE_BOUND": 0.10},
    "RANGE_BOUND": {"ACCUMULATION": 0.25, "DISTRIBUTION": 0.25, "TRENDING_BULLISH": 0.20, "TRENDING_BEARISH": 0.20},
    "LIQUIDITY_SWEEP": {"VOLATILE_BREAKOUT": 0.35, "RANGE_BOUND": 0.30, "MEAN_REVERSION": 0.20},
    "CRASH_EVENT": {"HIGH_VOLATILITY": 0.45, "MEAN_REVERSION": 0.25, "RANGE_BOUND": 0.15},
}


class RegimeMemory:
    """Persistent regime memory store with adaptive transition intelligence."""

    def __init__(self, path: str = DEFAULT_MEMORY_PATH, max_history: int = 400, **kwargs) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.max_history = max(1, int(max_history))
        self._payload = self._load()
        self.history: Deque[Dict[str, Any]] = deque(self._payload.get("history", []), maxlen=self.max_history)
        self.transitions: Dict[str, Dict[str, int]] = self._payload.setdefault("transitions", {})
        self.performance: Dict[str, Dict[str, Any]] = self._payload.setdefault("performance", {})
        self.regime_stats: Dict[str, Dict[str, Any]] = self._payload.setdefault("regime_stats", {})

    def add_regime_event(
        self,
        regime: str,
        duration: float = 1.0,
        volatility: float = 0.0,
        confidence: float = 0.0,
        pnl_impact: float = 0.0,
        strategy_id: Optional[str] = None,
        strategy_performance: Optional[Dict[str, Any]] = None,
        transition_from: Optional[str] = None,
        transition_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        regime_label = str(regime or "UNKNOWN").upper()
        timestamp = datetime.utcnow().isoformat() + "Z"
        payload = {
            "timestamp": timestamp,
            "regime": regime_label,
            "duration": float(duration or 1.0),
            "volatility": float(volatility or 0.0),
            "confidence": float(confidence or 0.0),
            "pnl_impact": float(pnl_impact or 0.0),
            "strategy_id": str(strategy_id or "UNKNOWN").upper(),
            "transition_from": str(transition_from or "UNKNOWN").upper(),
            "transition_hint": str(transition_hint or "UNKNOWN").upper(),
        }

        self.history.append(payload)
        self._payload["history"] = list(self.history)
        self._update_regime_stats(regime_label, duration, volatility, confidence)

        if strategy_id:
            self._update_strategy_performance(regime_label, strategy_id, pnl_impact, strategy_performance)

        if transition_from:
            self.record_transition(transition_from, regime_label)

        self._save()
        return {
            "expected_duration": self.expected_duration(regime_label),
            "historical_regime_similarity": self.historical_regime_similarity(regime_label, payload),
        }

    def record_transition(self, from_regime: str, to_regime: str) -> None:
        from_label = str(from_regime or "UNKNOWN").upper()
        to_label = str(to_regime or "UNKNOWN").upper()
        row = self.transitions.setdefault(from_label, {})
        row[to_label] = int(row.get(to_label, 0)) + 1
        self._payload["transitions"] = self.transitions
        self._save()

    def transition_probabilities(self, current_regime: str) -> Dict[str, float]:
        current = str(current_regime or "UNKNOWN").upper()
        counts = self.transitions.get(current, {})
        if not counts:
            return self._normalize_probabilities(DEFAULT_TRANSITION_PRIORS.get(current, {}))
        return self._normalize_probabilities({k: float(v) for k, v in counts.items()})

    def expected_duration(self, regime: str) -> float:
        regime_label = str(regime or "UNKNOWN").upper()
        stats = self.regime_stats.get(regime_label, {})
        occurrences = int(stats.get("occurrences", 0))
        total_duration = float(stats.get("total_duration", 0.0))
        if occurrences > 0:
            return round(total_duration / occurrences, 4)
        return float(DEFAULT_EXPECTED_DURATION.get(regime_label, 4.0))

    def historical_regime_similarity(self, regime: str, current_row: Dict[str, Any]) -> float:
        regime_label = str(regime or "UNKNOWN").upper()
        candidates = [row for row in self.history if row.get("regime") == regime_label]
        if not candidates:
            return 0.0
        comparator = self._normalize_features(current_row)
        scores = [self._compare_features(comparator, self._normalize_features(row)) for row in candidates[-10:]]
        return round(sum(scores) / max(1, len(scores)), 4)

    def strategy_metrics(self, strategy_id: str, regime: str) -> Dict[str, Any]:
        sid = str(strategy_id or "UNKNOWN").upper()
        reg = str(regime or "UNKNOWN").upper()
        metrics = self.performance.get(sid, {}).get(reg, {})
        return {
            "trades": int(metrics.get("trades", 0)),
            "wins": int(metrics.get("wins", 0)),
            "win_rate": float(metrics.get("win_rate", 0.0)),
            "pf": float(metrics.get("pf", 0.0)),
            "avg_pnl": float(metrics.get("avg_pnl", 0.0)),
        }

    def strategy_bias(self, strategy_id: str, regime: str) -> float:
        metrics = self.strategy_metrics(strategy_id, regime)
        trades = metrics["trades"]
        if trades < 6:
            return 0.0
        win_rate = metrics["win_rate"]
        pf = metrics["pf"]
        boost = 0.0
        if win_rate >= 0.60 and pf >= 1.2:
            boost += 10.0
        if win_rate >= 0.55 and pf >= 1.0:
            boost += 4.0
        if win_rate < 0.40 or pf < 0.9:
            boost -= 12.0
        return float(max(-20.0, min(boost, 12.0)))

    def _update_regime_stats(self, regime: str, duration: float, volatility: float, confidence: float) -> None:
        row = self.regime_stats.setdefault(
            regime,
            {
                "occurrences": 0,
                "total_duration": 0.0,
                "total_volatility": 0.0,
                "total_confidence": 0.0,
            },
        )
        row["occurrences"] += 1
        row["total_duration"] = float(row.get("total_duration", 0.0)) + float(duration or 1.0)
        row["total_volatility"] = float(row.get("total_volatility", 0.0)) + float(volatility or 0.0)
        row["total_confidence"] = float(row.get("total_confidence", 0.0)) + float(confidence or 0.0)
        self._payload["regime_stats"] = self.regime_stats

    def _update_strategy_performance(
        self,
        regime: str,
        strategy_id: str,
        pnl: float,
        strategy_performance: Optional[Dict[str, Any]] = None,
    ) -> None:
        sid = str(strategy_id or "UNKNOWN").upper()
        reg = str(regime or "UNKNOWN").upper()
        root = self.performance.setdefault(sid, {})
        row = root.setdefault(
            reg,
            {
                "trades": 0,
                "wins": 0,
                "pnl": 0.0,
                "loss": 0.0,
                "win_rate": 0.0,
                "pf": 1.0,
                "avg_pnl": 0.0,
            },
        )
        row["trades"] += 1
        row["wins"] += 1 if float(pnl or 0.0) > 0 else 0
        row["pnl"] = float(row.get("pnl", 0.0)) + float(pnl or 0.0)
        if float(pnl or 0.0) < 0:
            row["loss"] = float(row.get("loss", 0.0)) + abs(float(pnl or 0.0))
        closed = max(1, int(row.get("trades", 0)))
        row["avg_pnl"] = round(float(row.get("pnl", 0.0)) / closed, 6)
        if closed > 0:
            row["win_rate"] = round(float(row.get("wins", 0)) / closed, 4)
        loss = float(row.get("loss", 0.0))
        wins = float(row.get("pnl", 0.0)) if float(row.get("pnl", 0.0)) > 0 else 0.0
        row["pf"] = round((wins / loss) if loss > 0 else max(1.0, row.get("pf", 1.0)), 4)
        if strategy_performance:
            row["pf"] = round(max(row["pf"], float(strategy_performance.get("pf", row["pf"]))), 4)
            row["win_rate"] = round(max(row["win_rate"], float(strategy_performance.get("win_rate", row["win_rate"]))), 4)
        root[reg] = row
        self._payload["performance"] = self.performance

    def _normalize_probabilities(self, raw: Dict[str, float]) -> Dict[str, float]:
        total = sum(float(v or 0.0) for v in raw.values())
        if total <= 0:
            return {}
        return {k: round(float(v) / total, 4) for k, v in raw.items()}

    def _normalize_features(self, row: Dict[str, Any]) -> Dict[str, float]:
        return {
            "duration": float(row.get("duration", 1.0)) / 10.0,
            "volatility": float(row.get("volatility", 0.0)) / 100.0,
            "confidence": float(row.get("confidence", 0.0)) / 1.0,
        }

    def _compare_features(self, left: Dict[str, float], right: Dict[str, float]) -> float:
        distance = 0.0
        for key in left:
            distance += abs(left.get(key, 0.0) - right.get(key, 0.0))
        return round(max(0.0, 1.0 - min(distance / 3.0, 1.0)), 4)

    def _load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {"history": [], "transitions": {}, "performance": {}, "regime_stats": {}}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                payload.setdefault("history", [])
                payload.setdefault("transitions", {})
                payload.setdefault("performance", {})
                payload.setdefault("regime_stats", {})
                return payload
        except Exception:
            pass
        return {"history": [], "transitions": {}, "performance": {}, "regime_stats": {}}

    def _save(self) -> None:
        self.path.write_text(json.dumps(self._payload, indent=2), encoding="utf-8")

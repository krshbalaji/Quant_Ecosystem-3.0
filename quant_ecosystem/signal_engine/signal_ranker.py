"""Signal ranking module."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional


class SignalRanker:
    """Ranks confidence-scored signals and returns top-N per cycle."""

    def __init__(self, top_n: int = 10, min_confidence: float = 0.0, **kwargs):
        self.top_n = max(1, int(top_n))
        self.min_confidence = max(0.0, min(1.0, float(min_confidence)))

    def rank(self, signals: Iterable[Dict], top_n: Optional[int] = None) -> List[Dict]:
        rows = [dict(item) for item in signals]
        filtered = [row for row in rows if self._confidence(row) >= self.min_confidence]

        ranked = sorted(
            filtered,
            key=lambda row: (
                self._confidence(row),
                self._to_float(row.get("signal_strength", 0.0), 0.0),
                self._to_float(row.get("liquidity_score", 0.0), 0.0),
            ),
            reverse=True,
        )
        limit = self.top_n if top_n is None else max(1, int(top_n))
        return ranked[:limit]

    def summarize(self, ranked_signals: Iterable[Dict]) -> Dict:
        rows = list(ranked_signals)
        return {
            "count": len(rows),
            "top_symbols": [str(row.get("symbol", "")) for row in rows[:5]],
            "avg_confidence": round(
                sum(self._confidence(row) for row in rows) / max(1, len(rows)),
                6,
            ),
        }

    def _confidence(self, row: Dict) -> float:
        return self._to_float(row.get("confidence_score", row.get("confidence", 0.0)), 0.0)

    def _to_float(self, value, default: float = 0.0) -> float:
        try:
            if value is None:
                return float(default)
            return float(value)
        except (TypeError, ValueError):
            return float(default)


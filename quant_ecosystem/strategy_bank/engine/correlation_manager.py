"""Rolling correlation and cluster controls for strategy allocations."""

from __future__ import annotations

from typing import Dict, List, Tuple


class CorrelationManager:
    """Computes pairwise rolling correlation and returns allocation penalties."""

    def __init__(self, threshold: float = 0.7, **kwargs):
        self.threshold = float(threshold)

    def matrix(self, rows: List[Dict]) -> Dict[str, Dict[str, float]]:
        ids = [row.get("id") for row in rows]
        out: Dict[str, Dict[str, float]] = {item: {} for item in ids}
        for left in rows:
            left_id = left.get("id")
            left_series = list(left.get("returns", []))
            for right in rows:
                right_id = right.get("id")
                right_series = list(right.get("returns", []))
                out[left_id][right_id] = self._corr(left_series, right_series)
        return out

    def penalize(self, rows: List[Dict]) -> Dict[str, Dict]:
        result = {row.get("id"): {"penalty": 0.0, "cluster": "", "reduce": False} for row in rows}
        data = sorted(rows, key=lambda item: float(item.get("score", 0.0)))
        corr = self.matrix(rows)

        for i in range(len(data)):
            for j in range(i + 1, len(data)):
                left = data[i]
                right = data[j]
                left_id = left.get("id")
                right_id = right.get("id")
                pair_corr = abs(corr.get(left_id, {}).get(right_id, 0.0))
                if pair_corr <= self.threshold:
                    continue
                weaker_id, stronger_id = (left_id, right_id)
                penalty = round((pair_corr - self.threshold) * 100.0, 4)
                result[weaker_id]["penalty"] += penalty
                result[weaker_id]["reduce"] = True
                result[weaker_id]["cluster"] = f"cluster::{stronger_id}"
                if not result[stronger_id]["cluster"]:
                    result[stronger_id]["cluster"] = f"cluster::{stronger_id}"
        return result

    def _corr(self, left: List[float], right: List[float]) -> float:
        n = min(len(left), len(right), 100)
        if n < 5:
            return 0.0
        a = left[-n:]
        b = right[-n:]
        mean_a = sum(a) / n
        mean_b = sum(b) / n
        num = sum((a[k] - mean_a) * (b[k] - mean_b) for k in range(n))
        den_a = sum((x - mean_a) ** 2 for x in a) ** 0.5
        den_b = sum((x - mean_b) ** 2 for x in b) ** 0.5
        if den_a == 0 or den_b == 0:
            return 0.0
        return round(num / (den_a * den_b), 4)

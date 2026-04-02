"""Diversification engine for meta strategy portfolio construction."""

from __future__ import annotations

from math import sqrt
from typing import Dict, Iterable, List, Set


class StrategyDiversificationEngine:
    """Applies concentration and correlation controls across strategies."""

    def __init__(
        self,
        correlation_threshold: float = 0.75,
        max_per_family: int = 2,
        max_per_asset_class: int = 3,
        max_per_timeframe: int = 3, **kwargs
    ):
        self.correlation_threshold = max(0.0, min(0.99, float(correlation_threshold)))
        self.max_per_family = max(1, int(max_per_family))
        self.max_per_asset_class = max(1, int(max_per_asset_class))
        self.max_per_timeframe = max(1, int(max_per_timeframe))

    def select_diversified(self, ranked_rows: Iterable[Dict], max_active: int = 5) -> Dict:
        """Returns diversified active/reduced groups from ranked input rows."""
        selected: List[Dict] = []
        reduced: List[Dict] = []
        family_count: Dict[str, int] = {}
        asset_count: Dict[str, int] = {}
        timeframe_count: Dict[str, int] = {}

        for row in ranked_rows:
            if len(selected) >= max(1, int(max_active)):
                reduced.append(dict(row))
                continue

            family = self._family(row)
            asset_class = self._asset_class(row)
            timeframe = self._timeframe(row)

            if family_count.get(family, 0) >= self.max_per_family:
                reduced.append(self._with_reason(row, "family_limit"))
                continue
            if asset_count.get(asset_class, 0) >= self.max_per_asset_class:
                reduced.append(self._with_reason(row, "asset_class_limit"))
                continue
            if timeframe_count.get(timeframe, 0) >= self.max_per_timeframe:
                reduced.append(self._with_reason(row, "timeframe_limit"))
                continue
            if self._is_too_correlated(row, selected):
                reduced.append(self._with_reason(row, "correlation_limit"))
                continue

            selected.append(dict(row))
            family_count[family] = family_count.get(family, 0) + 1
            asset_count[asset_class] = asset_count.get(asset_class, 0) + 1
            timeframe_count[timeframe] = timeframe_count.get(timeframe, 0) + 1

        return {
            "active": selected,
            "reduced": reduced,
            "clusters": self._build_clusters(selected),
        }

    def _is_too_correlated(self, candidate: Dict, selected: List[Dict]) -> bool:
        for row in selected:
            if self._pair_correlation(candidate, row) > self.correlation_threshold:
                return True
        return False

    def _pair_correlation(self, left: Dict, right: Dict) -> float:
        cluster_l = str(left.get("correlation_cluster", "")).strip()
        cluster_r = str(right.get("correlation_cluster", "")).strip()
        if cluster_l and cluster_r and cluster_l == cluster_r:
            return 1.0

        returns_l = self._returns(left)
        returns_r = self._returns(right)
        if len(returns_l) < 8 or len(returns_r) < 8:
            return 0.0
        return abs(self._pearson(returns_l, returns_r))

    def _build_clusters(self, rows: Iterable[Dict]) -> Dict:
        by_family: Dict[str, Set[str]] = {}
        by_asset: Dict[str, Set[str]] = {}
        by_timeframe: Dict[str, Set[str]] = {}
        for row in rows:
            sid = str(row.get("id", "")).strip()
            if not sid:
                continue
            by_family.setdefault(self._family(row), set()).add(sid)
            by_asset.setdefault(self._asset_class(row), set()).add(sid)
            by_timeframe.setdefault(self._timeframe(row), set()).add(sid)
        return {
            "family": {key: sorted(list(value)) for key, value in by_family.items()},
            "asset_class": {key: sorted(list(value)) for key, value in by_asset.items()},
            "timeframe": {key: sorted(list(value)) for key, value in by_timeframe.items()},
        }

    def _family(self, row: Dict) -> str:
        return str(row.get("family", row.get("category", "systematic"))).strip().lower() or "systematic"

    def _asset_class(self, row: Dict) -> str:
        return str(row.get("asset_class", "stocks")).strip().lower() or "stocks"

    def _timeframe(self, row: Dict) -> str:
        return str(row.get("timeframe", "5m")).strip().lower() or "5m"

    def _returns(self, row: Dict) -> List[float]:
        metrics = row.get("metrics", row.get("raw_metrics", {}))
        src = metrics.get("returns", row.get("returns", []))
        out = []
        for item in src or []:
            try:
                out.append(float(item))
            except (TypeError, ValueError):
                continue
        return out[-120:]

    def _pearson(self, left: List[float], right: List[float]) -> float:
        n = min(len(left), len(right))
        if n < 2:
            return 0.0
        x = left[-n:]
        y = right[-n:]
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        num = 0.0
        den_x = 0.0
        den_y = 0.0
        for i in range(n):
            dx = x[i] - mean_x
            dy = y[i] - mean_y
            num += dx * dy
            den_x += dx * dx
            den_y += dy * dy
        den = sqrt(max(1e-12, den_x * den_y))
        return num / den

    def _with_reason(self, row: Dict, reason: str) -> Dict:
        item = dict(row)
        item["meta_reduction_reason"] = reason
        return item


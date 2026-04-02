"""Correlation estimation and clustering utilities for strategy rows."""

from __future__ import annotations

from math import sqrt
from typing import Dict, List


class CorrelationClusterer:
    """Builds pairwise correlation matrix and connected-component clusters."""

    def __init__(self, max_correlation: float = 0.75, **kwargs):
        self.max_correlation = max(0.0, min(0.99, float(max_correlation)))

    def analyze(self, strategy_rows: List[Dict]) -> Dict:
        """Return matrix + clusters based on return-series correlations."""
        ids = [self._sid(row) for row in strategy_rows if self._sid(row)]
        returns_map = {self._sid(row): self._returns(row) for row in strategy_rows if self._sid(row)}

        matrix: Dict[str, Dict[str, float]] = {sid: {} for sid in ids}
        for i, left in enumerate(ids):
            for j, right in enumerate(ids):
                if j < i:
                    matrix[left][right] = matrix[right][left]
                    continue
                if left == right:
                    matrix[left][right] = 1.0
                    continue
                corr = abs(self._pearson(returns_map.get(left, []), returns_map.get(right, [])))
                matrix[left][right] = corr
                matrix[right][left] = corr

        clusters = self._clusters(ids, matrix)
        cluster_map = {}
        for idx, cluster in enumerate(clusters):
            name = f"cluster_{idx + 1}"
            for sid in cluster:
                cluster_map[sid] = name

        return {
            "matrix": matrix,
            "clusters": clusters,
            "cluster_map": cluster_map,
        }

    def _clusters(self, ids: List[str], matrix: Dict[str, Dict[str, float]]) -> List[List[str]]:
        seen = set()
        out: List[List[str]] = []
        for sid in ids:
            if sid in seen:
                continue
            stack = [sid]
            component = []
            seen.add(sid)
            while stack:
                cur = stack.pop()
                component.append(cur)
                for peer, corr in matrix.get(cur, {}).items():
                    if peer in seen:
                        continue
                    if corr >= self.max_correlation:
                        seen.add(peer)
                        stack.append(peer)
            out.append(sorted(component))
        out.sort(key=lambda item: (-len(item), item))
        return out

    def _sid(self, row: Dict) -> str:
        return str(row.get("id", "")).strip()

    def _returns(self, row: Dict) -> List[float]:
        src = row.get("returns")
        if src is None and isinstance(row.get("metrics"), dict):
            src = row.get("metrics", {}).get("returns", [])
        out: List[float] = []
        for item in src or []:
            try:
                out.append(float(item))
            except (TypeError, ValueError):
                continue
        return out[-250:]

    def _pearson(self, left: List[float], right: List[float]) -> float:
        n = min(len(left), len(right))
        if n < 8:
            return 0.0
        x = left[-n:]
        y = right[-n:]
        mx = sum(x) / n
        my = sum(y) / n
        num = 0.0
        den_x = 0.0
        den_y = 0.0
        for i in range(n):
            dx = x[i] - mx
            dy = y[i] - my
            num += dx * dy
            den_x += dx * dx
            den_y += dy * dy
        den = sqrt(max(1e-12, den_x * den_y))
        return num / den


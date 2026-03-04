"""Correlation analysis for portfolio optimization."""

from __future__ import annotations

from math import sqrt
from typing import Dict, Iterable, List, Tuple


class CorrelationAnalyzer:
    """Builds correlation matrix and correlated clusters."""

    def __init__(self, threshold: float = 0.75):
        self.threshold = max(0.0, min(0.99, float(threshold)))

    def analyze(self, strategy_rows: Iterable[Dict]) -> Dict:
        rows = [dict(row) for row in strategy_rows if row.get("id")]
        ids = [str(row.get("id")) for row in rows]
        matrix: Dict[str, Dict[str, float]] = {sid: {} for sid in ids}

        for i in range(len(rows)):
            sid_i = ids[i]
            matrix[sid_i][sid_i] = 1.0
            for j in range(i + 1, len(rows)):
                sid_j = ids[j]
                corr = self._pair_corr(rows[i], rows[j])
                matrix[sid_i][sid_j] = corr
                matrix[sid_j][sid_i] = corr

        clusters = self._clusters(ids, matrix)
        return {"matrix": matrix, "clusters": clusters}

    def correlation_penalty(self, strategy_id: str, correlation_matrix: Dict[str, Dict[str, float]]) -> float:
        row = correlation_matrix.get(strategy_id, {})
        peers = [abs(v) for sid, v in row.items() if sid != strategy_id]
        if not peers:
            return 0.0
        high = [v for v in peers if v > self.threshold]
        if not high:
            return 0.0
        return round(sum(high) / len(high), 6)

    def _pair_corr(self, left: Dict, right: Dict) -> float:
        cluster_l = str(left.get("correlation_cluster", "")).strip()
        cluster_r = str(right.get("correlation_cluster", "")).strip()
        if cluster_l and cluster_r and cluster_l == cluster_r:
            return 0.95

        x = self._returns(left)
        y = self._returns(right)
        n = min(len(x), len(y))
        if n < 10:
            # fallback by family/asset similarity
            fam_l = str(left.get("family", left.get("category", ""))).lower()
            fam_r = str(right.get("family", right.get("category", ""))).lower()
            asset_l = str(left.get("asset_class", "")).lower()
            asset_r = str(right.get("asset_class", "")).lower()
            base = 0.0
            if fam_l and fam_l == fam_r:
                base += 0.45
            if asset_l and asset_l == asset_r:
                base += 0.35
            return min(0.95, base)
        x = x[-n:]
        y = y[-n:]
        mx = sum(x) / n
        my = sum(y) / n
        num = 0.0
        dxs = 0.0
        dys = 0.0
        for i in range(n):
            dx = x[i] - mx
            dy = y[i] - my
            num += dx * dy
            dxs += dx * dx
            dys += dy * dy
        den = sqrt(max(1e-12, dxs * dys))
        return max(-1.0, min(1.0, num / den))

    def _clusters(self, ids: List[str], matrix: Dict[str, Dict[str, float]]) -> List[List[str]]:
        clusters: List[List[str]] = []
        visited = set()
        for sid in ids:
            if sid in visited:
                continue
            cluster = [sid]
            visited.add(sid)
            for peer in ids:
                if peer in visited:
                    continue
                if abs(float(matrix.get(sid, {}).get(peer, 0.0))) >= self.threshold:
                    cluster.append(peer)
                    visited.add(peer)
            clusters.append(cluster)
        return clusters

    def _returns(self, row: Dict) -> List[float]:
        metrics = row.get("metrics", row.get("raw_metrics", {}))
        raw = metrics.get("returns", row.get("returns", []))
        out = []
        for value in raw or []:
            try:
                out.append(float(value))
            except (TypeError, ValueError):
                continue
        return out[-200:]


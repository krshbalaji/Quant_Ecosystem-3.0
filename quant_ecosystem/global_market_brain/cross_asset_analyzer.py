"""Cross-asset analyzer for macro market state."""

from __future__ import annotations

from typing import Dict, Iterable, List


class CrossAssetAnalyzer:
    """Analyzes correlation and stress patterns across asset classes."""

    def analyze(self, snapshots: Iterable[Dict]) -> Dict:
        rows = list(snapshots or [])
        by_asset: Dict[str, List[float]] = {}
        for row in rows:
            asset = str(row.get("asset_class", "unknown")).lower()
            by_asset.setdefault(asset, [])
            by_asset[asset].append(self._f(row.get("return", row.get("ret", 0.0))))

        # Compute light-weight pairwise correlation proxy without heavy deps.
        assets = sorted(by_asset.keys())
        corr_pairs = {}
        for i in range(len(assets)):
            for j in range(i + 1, len(assets)):
                a = assets[i]
                b = assets[j]
                corr = self._corr(by_asset.get(a, []), by_asset.get(b, []))
                corr_pairs[f"{a}:{b}"] = round(corr, 6)

        abs_corr = [abs(v) for v in corr_pairs.values()]
        avg_abs_corr = (sum(abs_corr) / len(abs_corr)) if abs_corr else 0.0
        stress_score = min(1.0, max(0.0, avg_abs_corr))
        return {
            "assets_seen": assets,
            "pair_correlations": corr_pairs,
            "avg_abs_correlation": round(avg_abs_corr, 6),
            "market_stress_score": round(stress_score, 6),
        }

    def _corr(self, a: List[float], b: List[float]) -> float:
        n = min(len(a), len(b))
        if n < 3:
            return 0.0
        x = a[-n:]
        y = b[-n:]
        mx = sum(x) / n
        my = sum(y) / n
        num = sum((x[i] - mx) * (y[i] - my) for i in range(n))
        denx = sum((x[i] - mx) ** 2 for i in range(n))
        deny = sum((y[i] - my) ** 2 for i in range(n))
        den = (denx * deny) ** 0.5
        if den <= 1e-12:
            return 0.0
        return max(-1.0, min(1.0, num / den))

    def _f(self, value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0


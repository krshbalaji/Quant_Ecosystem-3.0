"""Correlation and concentration monitor for portfolio risk governor."""

from __future__ import annotations

from typing import Dict, Iterable, List, Tuple


class CorrelationMonitor:
    """Flags excessive correlated exposure by matrix and concentration heuristics."""

    def __init__(self, threshold: float = 0.75, **kwargs):
        self.threshold = float(threshold)

    def evaluate(
        self,
        positions: Iterable[Dict],
        correlation_matrix: Dict[str, Dict[str, float]] | None = None,
    ) -> Dict:
        correlation_matrix = correlation_matrix or {}
        rows = [dict(p) for p in positions]
        symbols = [str(row.get("symbol", "")).strip() for row in rows if row.get("symbol")]
        notional_map = {
            str(row.get("symbol", "")).strip(): abs(float(row.get("notional", 0.0) or 0.0))
            for row in rows
            if row.get("symbol")
        }

        breaches = self._matrix_breaches(symbols, notional_map, correlation_matrix)
        cluster_breaches = self._cluster_breaches(rows)
        all_breaches = breaches + cluster_breaches
        return {
            "threshold": self.threshold,
            "breaches": all_breaches,
            "breached": bool(all_breaches),
        }

    def _matrix_breaches(
        self,
        symbols: List[str],
        notionals: Dict[str, float],
        matrix: Dict[str, Dict[str, float]],
    ) -> List[Dict]:
        out: List[Dict] = []
        for i in range(len(symbols)):
            for j in range(i + 1, len(symbols)):
                left = symbols[i]
                right = symbols[j]
                corr = abs(float(matrix.get(left, {}).get(right, 0.0)))
                if corr < self.threshold:
                    continue
                exposure = notionals.get(left, 0.0) + notionals.get(right, 0.0)
                out.append(
                    {
                        "type": "PAIR_CORRELATION",
                        "left": left,
                        "right": right,
                        "correlation": round(corr, 4),
                        "combined_notional": round(exposure, 4),
                        "action": "REDUCE_CORRELATED_EXPOSURE",
                    }
                )
        return out

    def _cluster_breaches(self, positions: List[Dict]) -> List[Dict]:
        """Fallback concentration checks for sector-like clusters."""
        totals: Dict[str, float] = {}
        overall = 0.0
        for row in positions:
            symbol = str(row.get("symbol", "")).strip()
            cluster = self._cluster(symbol)
            notional = abs(float(row.get("notional", 0.0) or 0.0))
            totals[cluster] = totals.get(cluster, 0.0) + notional
            overall += notional
        if overall <= 0:
            return []

        out: List[Dict] = []
        for cluster, total in totals.items():
            pct = (total / overall) * 100.0
            if pct < 60.0:
                continue
            out.append(
                {
                    "type": "CLUSTER_CONCENTRATION",
                    "cluster": cluster,
                    "exposure_pct": round(pct, 4),
                    "action": "REDUCE_CLUSTER_EXPOSURE",
                }
            )
        return out

    def _cluster(self, symbol: str) -> str:
        sym = symbol.upper()
        if "BANK" in sym:
            return "BANKING"
        if "NIFTY" in sym:
            return "INDEX"
        if sym.startswith("CRYPTO:"):
            return "CRYPTO"
        if sym.startswith("FX:"):
            return "FOREX"
        if sym.startswith("MCX:"):
            return "COMMODITY"
        return "EQUITY"


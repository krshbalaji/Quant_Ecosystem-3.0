"""Signal fusion module."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Optional

from quant_ecosystem.signal_engine.signal_confidence_engine import SignalConfidenceEngine
from quant_ecosystem.signal_engine.signal_ranker import SignalRanker


class SignalFusion:
    """Fuses signals from multiple sources and removes duplicates/correlation."""

    def __init__(
        self,
        confidence_engine: Optional[SignalConfidenceEngine] = None,
        ranker: Optional[SignalRanker] = None,
        max_per_symbol: int = 1,
        max_per_correlation_cluster: int = 2,
    ):
        self.confidence_engine = confidence_engine or SignalConfidenceEngine(min_confidence=0.0)
        self.ranker = ranker or SignalRanker(top_n=10, min_confidence=0.0)
        self.max_per_symbol = max(1, int(max_per_symbol))
        self.max_per_correlation_cluster = max(1, int(max_per_correlation_cluster))

    def fuse(
        self,
        strategy_bank_signals: Optional[Iterable[Dict]] = None,
        alpha_scanner_signals: Optional[Iterable[Dict]] = None,
        strategy_lab_signals: Optional[Iterable[Dict]] = None,
        context_map: Optional[Dict[str, Dict]] = None,
        top_n: int = 10,
    ) -> Dict:
        """Merge, deduplicate, score, cluster-filter, and rank."""
        merged = []
        merged.extend(self._attach_source(strategy_bank_signals or [], "strategy_bank"))
        merged.extend(self._attach_source(alpha_scanner_signals or [], "alpha_scanner"))
        merged.extend(self._attach_source(strategy_lab_signals or [], "strategy_lab"))

        deduped = self._dedupe(merged)
        scored = self.confidence_engine.score_batch(deduped, context_map=context_map)
        filtered = self._filter_correlation(scored)
        ranked = self.ranker.rank(filtered, top_n=top_n)

        return {
            "fused_signals": ranked,
            "all_scored": scored,
            "summary": self.ranker.summarize(ranked),
        }

    def connect_and_publish(
        self,
        fused_payload: Dict,
        strategy_selector=None,
        portfolio_ai=None,
        execution_engine=None,
    ) -> Dict:
        """Publish fused signal set to integrated modules."""
        rows = list(fused_payload.get("fused_signals", []))
        return self.confidence_engine.publish_to_engines(
            scored_signals=rows,
            strategy_selector=strategy_selector,
            portfolio_ai=portfolio_ai,
            execution_engine=execution_engine,
        )

    def _attach_source(self, rows: Iterable[Dict], source: str) -> List[Dict]:
        out = []
        for item in rows:
            row = dict(item)
            row.setdefault("source", source)
            row.setdefault("symbol", str(row.get("symbol", "")))
            row.setdefault("signal_type", str(row.get("signal_type", row.get("side", "UNKNOWN"))).upper())
            out.append(row)
        return out

    def _dedupe(self, rows: List[Dict]) -> List[Dict]:
        bucket: Dict[tuple, Dict] = {}
        for row in rows:
            key = (
                str(row.get("symbol", "")).strip(),
                str(row.get("signal_type", "")).strip().upper(),
                str(row.get("source", "")).strip(),
            )
            prev = bucket.get(key)
            if prev is None:
                bucket[key] = row
                continue
            # Keep stronger of duplicates by signal strength if present.
            prev_strength = self._to_float(prev.get("signal_strength", prev.get("confidence", 0.0)), 0.0)
            cur_strength = self._to_float(row.get("signal_strength", row.get("confidence", 0.0)), 0.0)
            if cur_strength > prev_strength:
                bucket[key] = row
        return list(bucket.values())

    def _filter_correlation(self, rows: List[Dict]) -> List[Dict]:
        by_symbol = defaultdict(int)
        by_cluster = defaultdict(int)
        out = []
        ranked = sorted(rows, key=lambda r: self._to_float(r.get("confidence_score", 0.0), 0.0), reverse=True)
        for row in ranked:
            symbol = str(row.get("symbol", "")).strip()
            cluster = str(row.get("correlation_cluster", row.get("asset_class", "uncategorized"))).strip()
            if by_symbol[symbol] >= self.max_per_symbol:
                continue
            if by_cluster[cluster] >= self.max_per_correlation_cluster:
                continue
            by_symbol[symbol] += 1
            by_cluster[cluster] += 1
            out.append(row)
        return out

    def _to_float(self, value, default: float = 0.0) -> float:
        try:
            if value is None:
                return float(default)
            return float(value)
        except (TypeError, ValueError):
            return float(default)


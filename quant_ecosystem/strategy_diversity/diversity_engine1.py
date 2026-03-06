"""Strategy Diversity Engine.

Provides concentration and correlation controls across strategy categories,
assets, and timeframes with integration hooks for Strategy Bank, Meta Brain,
and Portfolio AI.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from quant_ecosystem.strategy_diversity.correlation_clusterer import CorrelationClusterer
from quant_ecosystem.strategy_diversity.strategy_category_manager import StrategyCategoryManager


class StrategyDiversityEngine:
    """Central diversity governance layer for strategy ecosystems."""

    def __init__(
        self,
        max_strategies_per_category: int = 3,
        max_correlation: float = 0.75,
        max_per_asset_class: int = 4,
        max_per_timeframe: int = 4,
        category_manager: Optional[StrategyCategoryManager] = None,
        correlation_clusterer: Optional[CorrelationClusterer] = None,
    ):
        self.max_strategies_per_category = max(1, int(max_strategies_per_category))
        self.max_per_asset_class = max(1, int(max_per_asset_class))
        self.max_per_timeframe = max(1, int(max_per_timeframe))
        self.max_correlation = max(0.0, min(0.99, float(max_correlation)))
        self.category_manager = category_manager or StrategyCategoryManager()
        self.correlation_clusterer = correlation_clusterer or CorrelationClusterer(
            max_correlation=self.max_correlation
        )
        self.last_report: Dict = {}

    def evaluate_diversity(self, strategy_rows: Iterable[Dict]) -> Dict:
        """Evaluate concentration and correlation risk from strategy rows."""
        rows = [self.category_manager.enrich(row) for row in strategy_rows]
        corr = self.correlation_clusterer.analyze(rows)

        by_category = self._count(rows, "diversity_category")
        by_asset = self._count(rows, "asset_class")
        by_timeframe = self._count(rows, "timeframe")

        breaches = {
            "category": sorted(
                [k for k, v in by_category.items() if v > self.max_strategies_per_category]
            ),
            "asset_class": sorted(
                [k for k, v in by_asset.items() if v > self.max_per_asset_class]
            ),
            "timeframe": sorted(
                [k for k, v in by_timeframe.items() if v > self.max_per_timeframe]
            ),
            "correlation_clusters": [c for c in corr.get("clusters", []) if len(c) > 1],
        }

        report = {
            "max_strategies_per_category": self.max_strategies_per_category,
            "max_correlation": self.max_correlation,
            "counts": {
                "category": by_category,
                "asset_class": by_asset,
                "timeframe": by_timeframe,
            },
            "correlation": corr,
            "breaches": breaches,
        }
        self.last_report = report
        return report

    def apply_constraints(
        self,
        strategy_rows: Iterable[Dict],
        max_active: Optional[int] = None,
    ) -> Dict:
        """Return allowed + blocked strategy sets after diversity constraints."""
        rows = [self.category_manager.enrich(row) for row in strategy_rows]
        rows = sorted(rows, key=self._score_key, reverse=True)
        corr = self.correlation_clusterer.analyze(rows)
        cluster_map = corr.get("cluster_map", {})

        allowed: List[Dict] = []
        blocked: List[Dict] = []
        cat_count: Dict[str, int] = {}
        asset_count: Dict[str, int] = {}
        tf_count: Dict[str, int] = {}
        max_active_limit = max_active if max_active is not None else len(rows)

        for row in rows:
            sid = str(row.get("id", "")).strip()
            if not sid:
                continue
            row = dict(row)
            row["correlation_cluster"] = cluster_map.get(sid, row.get("correlation_cluster", ""))
            category = str(row.get("diversity_category", "momentum"))
            asset = str(row.get("asset_class", "stocks")).lower()
            timeframe = str(row.get("timeframe", "5m")).lower()

            reason = None
            if len(allowed) >= max_active_limit:
                reason = "max_active_limit"
            elif cat_count.get(category, 0) >= self.max_strategies_per_category:
                reason = "category_limit"
            elif asset_count.get(asset, 0) >= self.max_per_asset_class:
                reason = "asset_class_limit"
            elif tf_count.get(timeframe, 0) >= self.max_per_timeframe:
                reason = "timeframe_limit"
            elif self._is_cluster_conflict(row, allowed):
                reason = "correlation_limit"

            if reason:
                row["diversity_blocked"] = True
                row["diversity_reason"] = reason
                row["active"] = False
                blocked.append(row)
                continue

            row["diversity_blocked"] = False
            row["diversity_reason"] = ""
            allowed.append(row)
            cat_count[category] = cat_count.get(category, 0) + 1
            asset_count[asset] = asset_count.get(asset, 0) + 1
            tf_count[timeframe] = tf_count.get(timeframe, 0) + 1

        summary = {
            "allowed_ids": [str(row.get("id")) for row in allowed if row.get("id")],
            "blocked_ids": [str(row.get("id")) for row in blocked if row.get("id")],
            "allowed": allowed,
            "blocked": blocked,
            "correlation": corr,
        }
        self.last_report = {**(self.last_report or {}), "constraints": summary}
        return summary

    def integrate_strategy_bank(self, strategy_bank_layer, result: Dict) -> Dict:
        """Persist diversity metadata back into Strategy Bank registry."""
        if not (strategy_bank_layer and hasattr(strategy_bank_layer, "is_enabled") and strategy_bank_layer.is_enabled()):
            return {"updated": 0}
        updated = 0
        try:
            registry = strategy_bank_layer.bank_engine.registry
            for row in result.get("allowed", []) + result.get("blocked", []):
                sid = str(row.get("id", "")).strip()
                if not sid:
                    continue
                current = registry.get(sid) or {"id": sid}
                item = dict(current)
                item["category"] = row.get("diversity_category", row.get("category", "momentum"))
                item["correlation_cluster"] = row.get("correlation_cluster", item.get("correlation_cluster", ""))
                item["diversity_blocked"] = bool(row.get("diversity_blocked", False))
                item["diversity_reason"] = str(row.get("diversity_reason", ""))
                registry.upsert(item)
                updated += 1
            registry.save()
        except Exception:
            return {"updated": 0}
        return {"updated": updated}

    def integrate_meta_brain(self, meta_strategy_brain, result: Dict) -> Dict:
        """Expose diversity decision payload to Meta Strategy Brain."""
        if meta_strategy_brain is None:
            return {"applied": False}
        payload = {
            "allowed_ids": list(result.get("allowed_ids", [])),
            "blocked_ids": list(result.get("blocked_ids", [])),
            "counts": {
                "allowed": len(result.get("allowed_ids", [])),
                "blocked": len(result.get("blocked_ids", [])),
            },
        }
        try:
            setattr(meta_strategy_brain, "last_diversity_decision", payload)
            return {"applied": True, "payload": payload}
        except Exception:
            return {"applied": False}

    def integrate_portfolio_ai(self, portfolio_ai, result: Dict, allocations: Optional[Dict[str, float]] = None) -> Dict:
        """Apply diversity guardrails to Portfolio AI allocation map."""
        if portfolio_ai is None:
            return {"applied": False, "allocations": allocations or {}}
        base_alloc = dict(allocations or getattr(portfolio_ai, "last_allocation", {}) or {})
        if not base_alloc:
            base_alloc = {sid: 0.0 for sid in result.get("allowed_ids", [])}

        blocked_ids = set(result.get("blocked_ids", []))
        for sid in list(base_alloc.keys()):
            if sid in blocked_ids:
                base_alloc[sid] = 0.0

        normalized = self._normalize(base_alloc)
        try:
            setattr(portfolio_ai, "last_diversity_filtered_allocations", normalized)
            return {"applied": True, "allocations": normalized}
        except Exception:
            return {"applied": False, "allocations": normalized}

    def run_cycle(
        self,
        strategy_rows: Optional[Iterable[Dict]] = None,
        strategy_bank_layer=None,
        meta_strategy_brain=None,
        portfolio_ai=None,
        max_active: Optional[int] = None,
        allocations: Optional[Dict[str, float]] = None,
    ) -> Dict:
        """End-to-end diversity cycle with optional integration targets."""
        rows = list(strategy_rows) if strategy_rows is not None else self._rows_from_bank(strategy_bank_layer)
        eval_report = self.evaluate_diversity(rows)
        constrained = self.apply_constraints(rows, max_active=max_active)
        bank_result = self.integrate_strategy_bank(strategy_bank_layer, constrained)
        meta_result = self.integrate_meta_brain(meta_strategy_brain, constrained)
        port_result = self.integrate_portfolio_ai(portfolio_ai, constrained, allocations=allocations)
        return {
            "evaluation": eval_report,
            "constraints": constrained,
            "strategy_bank": bank_result,
            "meta_brain": meta_result,
            "portfolio_ai": port_result,
        }

    def _rows_from_bank(self, strategy_bank_layer) -> List[Dict]:
        if not (strategy_bank_layer and hasattr(strategy_bank_layer, "is_enabled") and strategy_bank_layer.is_enabled()):
            return []
        try:
            return list(strategy_bank_layer.registry_rows())
        except Exception:
            return []

    def _is_cluster_conflict(self, candidate: Dict, selected: List[Dict]) -> bool:
        cluster = str(candidate.get("correlation_cluster", "")).strip()
        if not cluster:
            return False
        for row in selected:
            if str(row.get("correlation_cluster", "")).strip() == cluster:
                return True
        return False

    def _score_key(self, row: Dict) -> float:
        for key in ("meta_score", "score", "sharpe"):
            try:
                return float(row.get(key, 0.0))
            except (TypeError, ValueError):
                continue
        return 0.0

    def _count(self, rows: List[Dict], field: str) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for row in rows:
            value = str(row.get(field, "unknown")).strip().lower() or "unknown"
            out[value] = out.get(value, 0) + 1
        return out

    def _normalize(self, allocations: Dict[str, float]) -> Dict[str, float]:
        total = sum(max(0.0, float(v)) for v in allocations.values())
        if total <= 1e-9:
            return {k: 0.0 for k in allocations}
        return {
            sid: round((max(0.0, float(weight)) / total) * 100.0, 6)
            for sid, weight in allocations.items()
        }



# ---------------------------------------------------------------------------
# SystemFactory-compatible alias
# ---------------------------------------------------------------------------

class DiversityEngine:
    """Minimal SystemFactory entry-point for diversity enforcement.

    Delegates to :class:`StrategyDiversityEngine` when available.
    """

    def __init__(self) -> None:
        import logging as _logging
        self._log = _logging.getLogger(__name__)
        self._delegate = None
        try:
            self._delegate = StrategyDiversityEngine()
        except Exception as exc:  # noqa: BLE001
            self._log.warning("DiversityEngine: delegate unavailable (%s) — stub mode", exc)
        self._log.info("DiversityEngine initialized")

    def filter_correlated(self, strategies: list, returns: dict | None = None) -> list:
        """Remove correlated strategies from *strategies*.

        *returns* is an optional ``{strategy_id: [float]}`` mapping of
        return series used to compute pairwise correlations.
        Falls back to returning all strategies when the delegate fails.
        """
        if self._delegate is not None:
            try:
                return self._delegate.enforce_diversity(
                    strategies=strategies, returns=returns or {}
                )
            except Exception as exc:  # noqa: BLE001
                self._log.warning("DiversityEngine.filter_correlated: delegate error (%s)", exc)
        return list(strategies)

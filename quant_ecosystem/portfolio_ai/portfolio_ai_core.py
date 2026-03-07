"""Portfolio AI core orchestrator."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Dict, Iterable, List, Optional

from quant_ecosystem.portfolio_ai.allocation_optimizer import AllocationOptimizer
from quant_ecosystem.portfolio_ai.correlation_analyzer import CorrelationAnalyzer
from quant_ecosystem.portfolio_ai.portfolio_state_manager import PortfolioStateManager
from quant_ecosystem.portfolio_ai.risk_parity_engine import RiskParityEngine
from quant_ecosystem.portfolio_ai.volatility_targeting import VolatilityTargeting


class PortfolioAI:
    """Dynamic portfolio optimization engine with publish hooks."""

    def __init__(
        self,
        strategy_bank_layer=None,
        capital_allocator_engine=None,
        strategy_selector=None,
        meta_strategy_brain=None,
        risk_engine=None,
        allocation_optimizer: Optional[AllocationOptimizer] = None,
        risk_parity_engine: Optional[RiskParityEngine] = None,
        correlation_analyzer: Optional[CorrelationAnalyzer] = None,
        volatility_targeting: Optional[VolatilityTargeting] = None,
        state_manager: Optional[PortfolioStateManager] = None, **kwargs
    ):
        self.strategy_bank_layer = strategy_bank_layer
        self.capital_allocator_engine = capital_allocator_engine
        self.strategy_selector = strategy_selector
        self.meta_strategy_brain = meta_strategy_brain
        self.risk_engine = risk_engine
        self.correlation_analyzer = correlation_analyzer or CorrelationAnalyzer(threshold=0.75)
        self.allocation_optimizer = allocation_optimizer or AllocationOptimizer(
            correlation_analyzer=self.correlation_analyzer
        )
        self.risk_parity_engine = risk_parity_engine or RiskParityEngine()
        self.volatility_targeting = volatility_targeting or VolatilityTargeting(target_volatility=0.10)
        self.state_manager = state_manager or PortfolioStateManager()

    def evaluate_portfolio(self, strategy_rows: Iterable[Dict] | None = None) -> Dict:
        rows = list(strategy_rows) if strategy_rows is not None else self._fetch_rows()
        corr = self.correlation_analyzer.analyze(rows)
        return {
            "strategy_count": len(rows),
            "correlation_clusters": corr.get("clusters", []),
            "correlation_matrix": corr.get("matrix", {}),
        }

    def optimize_allocations(self, strategy_rows: Iterable[Dict] | None = None, capital_pct: float = 100.0) -> Dict:
        start = time.perf_counter()
        rows = list(strategy_rows) if strategy_rows is not None else self._fetch_rows()
        if not rows:
            return {"allocations": {}, "latency_sec": 0.0, "state": self.state_manager.latest()}

        opt = self.allocation_optimizer.optimize(rows, capital_pct=capital_pct)
        rp_weights = self.risk_parity_engine.compute_weights(rows, capital_pct=capital_pct)
        merged = self._blend(opt["weights"], rp_weights, w_opt=0.6, w_rp=0.4)
        vol_targeted = self.volatility_targeting.scale_allocations(merged, rows)
        final_alloc = vol_targeted["allocations"]
        risk_contrib = self.risk_parity_engine.risk_contributions(final_alloc, rows)

        state = self.state_manager.update(
            allocations=final_alloc,
            strategy_rows=rows,
            risk_contributions=risk_contrib,
            correlation_clusters=opt.get("correlation_clusters", []),
        )
        latency = round(time.perf_counter() - start, 6)
        return {
            "allocations": final_alloc,
            "volatility_targeting": vol_targeted,
            "scores": opt.get("scores", {}),
            "correlation_clusters": opt.get("correlation_clusters", []),
            "risk_contributions": risk_contrib,
            "state": state,
            "latency_sec": latency,
        }

    def apply_risk_controls(self, allocations: Dict[str, float]) -> Dict[str, float]:
        if not allocations:
            return {}
        capped = dict(allocations)
        max_strategy_cap = 25.0
        if self.risk_engine is not None:
            try:
                max_strategy_cap = min(max_strategy_cap, float(getattr(self.risk_engine, "max_strategy_exposure_pct", 25.0)))
            except Exception:
                pass
        for sid in list(capped.keys()):
            capped[sid] = min(float(capped[sid]), max_strategy_cap)
        return self._normalize(capped)

    def publish_allocations(self, allocations: Dict[str, float], regime: str = "RANGE_BOUND") -> Dict:
        """Publish optimized weights to allocator/selector/meta/strategy-bank."""
        allocations = self.apply_risk_controls(allocations)
        self._publish_to_strategy_bank(allocations)
        self._publish_to_capital_allocator(allocations, regime=regime)
        self._publish_to_selector(allocations)
        self._publish_to_meta(allocations, regime=regime)

        decision = []
        clusters = self.state_manager.latest().get("correlation_clusters", [])
        cluster_map = {}
        for idx, cluster in enumerate(clusters):
            for sid in cluster:
                cluster_map[str(sid)] = f"cluster_{idx+1}"
        risk_contrib = self.state_manager.latest().get("risk_contributions", {})
        for sid, weight in allocations.items():
            decision.append(
                {
                    "strategy_id": str(sid),
                    "allocation_pct": round(float(weight), 6),
                    "volatility_contribution": round(float(risk_contrib.get(str(sid), 0.0)), 6),
                    "correlation_cluster": cluster_map.get(str(sid), ""),
                }
            )
        return {
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "allocations": allocations,
            "decision": decision,
        }

    def run_cycle(self, strategy_rows: Iterable[Dict] | None = None, regime: str = "RANGE_BOUND", capital_pct: float = 100.0) -> Dict:
        """Full cycle: evaluate -> optimize -> risk controls -> publish."""
        optimized = self.optimize_allocations(strategy_rows=strategy_rows, capital_pct=capital_pct)
        published = self.publish_allocations(optimized.get("allocations", {}), regime=regime)
        return {
            "optimized": optimized,
            "published": published,
            "state": self.state_manager.latest(),
        }

    def _fetch_rows(self) -> List[Dict]:
        layer = self.strategy_bank_layer
        if layer and hasattr(layer, "is_enabled") and layer.is_enabled():
            try:
                return list(layer.registry_rows())
            except Exception:
                return []
        return []

    def _blend(self, left: Dict[str, float], right: Dict[str, float], w_opt: float, w_rp: float) -> Dict[str, float]:
        ids = set(left.keys()) | set(right.keys())
        out = {}
        for sid in ids:
            a = float(left.get(sid, 0.0))
            b = float(right.get(sid, 0.0))
            out[sid] = (a * w_opt) + (b * w_rp)
        return self._normalize(out)

    def _normalize(self, allocations: Dict[str, float]) -> Dict[str, float]:
        total = sum(max(0.0, float(v)) for v in allocations.values())
        if total <= 1e-9:
            return {k: 0.0 for k in allocations}
        return {k: round((max(0.0, float(v)) / total) * 100.0, 6) for k, v in allocations.items()}

    def _publish_to_strategy_bank(self, allocations: Dict[str, float]) -> None:
        layer = self.strategy_bank_layer
        if not (layer and hasattr(layer, "is_enabled") and layer.is_enabled()):
            return
        try:
            reg = layer.bank_engine.registry
            rows = layer.registry_rows()
            for row in rows:
                sid = str(row.get("id", "")).strip()
                if not sid:
                    continue
                item = dict(row)
                item["allocation_pct"] = float(allocations.get(sid, 0.0))
                reg.upsert(item)
            reg.save()
        except Exception:
            return

    def _publish_to_capital_allocator(self, allocations: Dict[str, float], regime: str) -> None:
        allocator = self.capital_allocator_engine
        if allocator is None:
            return
        try:
            allocator.last_allocation = dict(allocations)
            setattr(allocator, "last_regime", str(regime).upper())
        except Exception:
            return

    def _publish_to_selector(self, allocations: Dict[str, float]) -> None:
        selector = self.strategy_selector
        if selector is None:
            return
        try:
            selected_ids = [sid for sid, w in allocations.items() if float(w) > 0]
            activation = selector.activation_manager.apply_selection(
                selected_ids=selected_ids,
                available_ids=selected_ids,
            )
            setattr(selector, "last_activation", activation)
        except Exception:
            return

    def _publish_to_meta(self, allocations: Dict[str, float], regime: str) -> None:
        brain = self.meta_strategy_brain
        if brain is None:
            return
        try:
            setattr(brain, "last_allocation", dict(allocations))
            setattr(brain, "last_regime", str(regime).upper())
        except Exception:
            return


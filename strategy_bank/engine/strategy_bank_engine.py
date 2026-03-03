"""Institutional Strategy Bank Engine.

This module is additive and optional. It never bypasses existing risk checks and only
produces policy metadata (active flags, stage, allocation).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from core.config_loader import Config
from strategy_bank.engine.capital_allocator import CapitalAllocator
from strategy_bank.engine.correlation_manager import CorrelationManager
from strategy_bank.engine.lifecycle_manager import LifecycleManager
from strategy_bank.engine.regime_mapper import RegimeMapper
from strategy_bank.engine.strategy_registry import StrategyRegistryStore


class StrategyBankEngine:
    """Institutional policy layer for strategy lifecycle and allocation."""

    def __init__(
        self,
        config: Optional[Config] = None,
        registry: Optional[StrategyRegistryStore] = None,
        lifecycle: Optional[LifecycleManager] = None,
        correlation: Optional[CorrelationManager] = None,
        allocator: Optional[CapitalAllocator] = None,
        regime_mapper: Optional[RegimeMapper] = None,
    ):
        self.config = config or Config()
        self.enabled = bool(getattr(self.config, "enable_strategy_bank", True))
        self.registry = registry or StrategyRegistryStore()
        self.lifecycle = lifecycle or LifecycleManager(
            min_trades_for_promotion=getattr(self.config, "min_trades_for_promotion", 100),
            retire_dd_threshold=getattr(self.config, "hard_drawdown_limit_pct", 20.0),
        )
        self.correlation = correlation or CorrelationManager(
            threshold=getattr(self.config, "correlation_threshold", 0.7)
        )
        self.allocator = allocator or CapitalAllocator(
            max_per_strategy_pct=getattr(self.config, "max_strategy_capital_pct", 30.0)
        )
        self.regime_mapper = regime_mapper or RegimeMapper()
        self.transition_dir = Path("reporting/output/strategy_transitions")
        self.transition_dir.mkdir(parents=True, exist_ok=True)
        self._allocation_map: Dict[str, float] = {}
        self._active_ids: List[str] = []
        self._last_regime = "RANGING"

    def ingest_reports(
        self,
        strategy_reports: List[Dict],
        intelligence_report: Optional[Dict] = None,
    ) -> List[Dict]:
        """Ingest evaluator reports and return enriched policy reports."""
        if not self.enabled:
            return strategy_reports

        regime = self.regime_mapper.normalize(intelligence_report or {})
        self._last_regime = regime
        normalized = [self._normalize_report(item) for item in strategy_reports]

        correlation_penalties = self.correlation.penalize(normalized)
        for row in normalized:
            sid = row["id"]
            payload = correlation_penalties.get(sid, {})
            row["correlation_penalty"] = round(float(payload.get("penalty", 0.0)), 4)
            row["correlation_cluster"] = payload.get("cluster", "")

            score = self._score(row)
            row["score"] = round(score, 4)
            row["disabled_by_correlation"] = bool(payload.get("reduce", False))

            next_stage, reason = self.lifecycle.evaluate(row)
            if next_stage != row["stage"]:
                self._log_transition(
                    strategy_id=sid,
                    previous=row["stage"],
                    new=next_stage,
                    reason=reason,
                    regime=regime,
                )
            row["stage"] = next_stage

            row["active"] = (
                row["stage"] in {"PAPER", "SHADOW", "LIVE"}
                and not row["disabled_by_correlation"]
                and self.regime_mapper.enabled_for_regime(row, regime)
            )

        ranked = sorted(normalized, key=lambda item: float(item.get("score", 0.0)), reverse=True)
        self._allocation_map = self.allocator.allocate(ranked)
        for row in ranked:
            row["allocation_pct"] = float(self._allocation_map.get(row["id"], 0.0))
            row["active"] = bool(row.get("active")) and row["allocation_pct"] > 0
            self.registry.upsert(row)

        self.registry.save()
        self._active_ids = [row["id"] for row in ranked if row.get("active")]
        return [self._to_legacy_report(row) for row in ranked]

    def get_active_strategies(self) -> List[str]:
        return list(self._active_ids)

    def get_allocation(self, strategy_id: str) -> float:
        return float(self._allocation_map.get(strategy_id, 0.0))

    def update_performance(self, strategy_id: str, metrics: Dict) -> None:
        """Update strategy-level metrics without touching trade execution."""
        if not self.enabled:
            return
        self.registry.update_metrics(strategy_id, metrics)

    def _normalize_report(self, report: Dict) -> Dict:
        metrics = report.get("metrics", {})
        stage = str(report.get("stage", "CANDIDATE")).upper()
        if stage == "PAPER_SHADOW":
            stage = "SHADOW"
        if stage == "REJECTED":
            stage = "CANDIDATE"

        regime_pref = report.get("regime_preference") or report.get("supported_regimes") or [
            "TRENDING",
            "RANGING",
            "HIGH_VOL",
            "LOW_VOL",
            "CRASH",
        ]
        return {
            "id": report.get("id"),
            "asset_class": report.get("asset_class", "stocks"),
            "timeframe": report.get("timeframe", "5m"),
            "category": report.get("category", "systematic"),
            "regime_preference": [str(item).upper() for item in regime_pref],
            "sharpe": float(metrics.get("sharpe", 0.0)),
            "profit_factor": float(metrics.get("profit_factor", 0.0)),
            "max_drawdown": float(metrics.get("max_dd", metrics.get("max_drawdown", 0.0))),
            "win_rate": float(metrics.get("win_rate", 0.0)),
            "expectancy": float(metrics.get("expectancy", 0.0)),
            "active": False,
            "allocation_pct": float(report.get("allocation_pct", 0.0)),
            "correlation_cluster": str(report.get("correlation_cluster", "")),
            "stage": stage,
            "score": float(report.get("score", 0.0)),
            "sample_size": int(metrics.get("sample_size", len(metrics.get("returns", [])))),
            "returns": list(metrics.get("returns", [])),
            "raw_metrics": metrics,
        }

    def _to_legacy_report(self, row: Dict) -> Dict:
        stage = row.get("stage", "CANDIDATE")
        legacy_stage = {
            "CANDIDATE": "REJECTED",
            "BACKTESTED": "PAPER",
            "PAPER": "PAPER",
            "SHADOW": "PAPER_SHADOW",
            "LIVE": "LIVE",
            "RETIRED": "RETIRED",
        }.get(stage, "REJECTED")
        metrics = dict(row.get("raw_metrics", {}))
        metrics.setdefault("max_dd", row.get("max_drawdown", 0.0))
        metrics.setdefault("sample_size", row.get("sample_size", 0))
        return {
            "id": row.get("id"),
            "name": row.get("id"),
            "metrics": metrics,
            "score": round(float(row.get("score", 0.0)), 4),
            "stage": legacy_stage,
            "correlation_penalty": round(float(row.get("correlation_penalty", 0.0)), 4),
            "disabled_by_correlation": bool(row.get("disabled_by_correlation", False)),
            "active": bool(row.get("active", False)),
            "allocation_pct": round(float(row.get("allocation_pct", 0.0)), 4),
            "correlation_cluster": row.get("correlation_cluster", ""),
            "asset_class": row.get("asset_class", "stocks"),
            "timeframe": row.get("timeframe", "5m"),
            "category": row.get("category", "systematic"),
            "regime_preference": list(row.get("regime_preference", [])),
        }

    def _score(self, row: Dict) -> float:
        return (
            0.25 * float(row.get("sharpe", 0.0))
            + 0.25 * float(row.get("profit_factor", 0.0))
            + 0.20 * float(row.get("expectancy", 0.0))
            + 0.15 * float(row.get("win_rate", 0.0))
            - 0.15 * float(row.get("max_drawdown", 0.0))
            - float(row.get("correlation_penalty", 0.0))
        )

    def _log_transition(self, strategy_id: str, previous: str, new: str, reason: str, regime: str) -> None:
        payload = {
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "strategy_id": strategy_id,
            "from": previous,
            "to": new,
            "reason": reason,
            "regime": regime,
        }
        path = self.transition_dir / f"transitions_{datetime.utcnow().strftime('%Y%m%d')}.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")

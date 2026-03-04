"""Adaptive Learning Engine."""

from __future__ import annotations

import time
from typing import Dict, Iterable, List, Optional

from quant_ecosystem.adaptive_learning.learning_memory import LearningMemory
from quant_ecosystem.adaptive_learning.parameter_optimizer import ParameterOptimizer
from quant_ecosystem.adaptive_learning.regime_performance_analyzer import RegimePerformanceAnalyzer
from quant_ecosystem.adaptive_learning.trade_feedback_collector import TradeFeedbackCollector


class AdaptiveLearningEngine:
    """Continuously learns from trade outcomes and emits parameter updates."""

    def __init__(
        self,
        trade_feedback_collector: Optional[TradeFeedbackCollector] = None,
        learning_memory: Optional[LearningMemory] = None,
        regime_performance_analyzer: Optional[RegimePerformanceAnalyzer] = None,
        parameter_optimizer: Optional[ParameterOptimizer] = None,
    ):
        self.trade_feedback_collector = trade_feedback_collector or TradeFeedbackCollector()
        self.learning_memory = learning_memory or LearningMemory()
        self.regime_performance_analyzer = regime_performance_analyzer or RegimePerformanceAnalyzer()
        self.parameter_optimizer = parameter_optimizer or ParameterOptimizer()
        self.last_updates: Dict = {}

    def ingest_trade_result(self, trade_result: Dict, defaults: Optional[Dict] = None) -> Dict:
        """Process one trade feedback row and produce learning update."""
        started = time.perf_counter()
        feedback = self.trade_feedback_collector.collect_trade(trade_result, defaults=defaults)
        self.learning_memory.add_feedback(feedback)
        self.learning_memory.save()
        update = self._build_updates([feedback["strategy_id"]])
        latency_sec = time.perf_counter() - started
        update["latency_ms"] = round(latency_sec * 1000.0, 3)
        self.last_updates = update
        return update

    def ingest_trade_batch(self, trades: Iterable[Dict], defaults: Optional[Dict] = None) -> Dict:
        """Batch learning during low activity windows."""
        started = time.perf_counter()
        feedback_rows = self.trade_feedback_collector.collect_batch(trades, defaults=defaults)
        touched = set()
        for row in feedback_rows:
            self.learning_memory.add_feedback(row)
            touched.add(row["strategy_id"])
        self.learning_memory.save()
        update = self._build_updates(sorted(touched))
        latency_sec = time.perf_counter() - started
        update["latency_ms"] = round(latency_sec * 1000.0, 3)
        self.last_updates = update
        return update

    def _build_updates(self, strategy_ids: List[str]) -> Dict:
        regime_rows = self.learning_memory.strategy_regime_rows()
        regime_perf = self.regime_performance_analyzer.analyze(regime_rows)

        updates = []
        for sid in strategy_ids:
            rows = [row for row in regime_rows if str(row.get("strategy_id")) == sid]
            optimization = self.parameter_optimizer.optimize(
                strategy_id=sid,
                regime_rows=rows,
                current_params={},
            )
            updates.append(
                {
                    "strategy_id": sid,
                    "parameter_updates": optimization.get("parameter_updates", {}),
                    "regime_performance": regime_perf.get("strategies", {}).get(sid, {}),
                    "learning_score": optimization.get("learning_score", 0.0),
                }
            )

        return {
            "updates": updates,
            "regime_performance_all": regime_perf,
        }

    def publish_updates(
        self,
        updates_payload: Dict,
        strategy_lab=None,
        meta_strategy_brain=None,
        portfolio_ai=None,
        execution_intelligence=None,
    ) -> Dict:
        """Publish learning updates to integrated modules (loose coupling)."""
        updates = list(updates_payload.get("updates", []))
        if strategy_lab is not None:
            try:
                setattr(strategy_lab, "last_learning_updates", updates)
            except Exception:
                pass
        if meta_strategy_brain is not None:
            try:
                setattr(meta_strategy_brain, "last_learning_updates", updates)
            except Exception:
                pass
        if portfolio_ai is not None:
            try:
                setattr(portfolio_ai, "last_learning_updates", updates)
            except Exception:
                pass
        if execution_intelligence is not None:
            try:
                setattr(execution_intelligence, "last_learning_updates", updates)
            except Exception:
                pass
        return {"published": len(updates)}


"""Worker node implementation for Alpha Grid."""

from __future__ import annotations

from typing import Any, Dict


class WorkerNode:
    """Executes grid tasks against injected engines."""

    SUPPORTED_TASKS = {
        "GENOME_GENERATION",
        "BACKTEST",
        "STRATEGY_EVALUATION",
        "SHADOW_ANALYSIS",
    }

    def __init__(
        self,
        node_id: str,
        genome_generator=None,
        genome_evaluator=None,
        strategy_lab=None,
        shadow_trading_engine=None,
    ):
        self.node_id = str(node_id)
        self.genome_generator = genome_generator
        self.genome_evaluator = genome_evaluator
        self.strategy_lab = strategy_lab
        self.shadow_trading_engine = shadow_trading_engine
        self.status = "IDLE"
        self.tasks_processed = 0
        self.tasks_failed = 0

    def execute(self, task_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        t = str(task_type or "").upper().strip()
        self.status = "BUSY"
        try:
            if t == "GENOME_GENERATION":
                out = self._genome_generation(payload)
            elif t == "BACKTEST":
                out = self._backtest(payload)
            elif t == "STRATEGY_EVALUATION":
                out = self._strategy_evaluation(payload)
            elif t == "SHADOW_ANALYSIS":
                out = self._shadow_analysis(payload)
            else:
                raise ValueError(f"unsupported_task_type:{t}")
            self.tasks_processed += 1
            return {"ok": True, "node_id": self.node_id, "task_type": t, "result": out}
        except Exception as exc:
            self.tasks_failed += 1
            return {"ok": False, "node_id": self.node_id, "task_type": t, "error": str(exc)}
        finally:
            self.status = "IDLE"

    def _genome_generation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if self.genome_generator is None:
            return {"generated": []}
        mode = str(payload.get("mode", "random")).lower()
        if mode == "mutation":
            parents = payload.get("parents", [])
            variants = int(payload.get("variants_per_base", 2))
            generated = self.genome_generator.generate_from_mutation(parents, variants_per_base=max(1, variants))
        elif mode == "crossbreed":
            parents = payload.get("parents", [])
            children = int(payload.get("children_count", 10))
            generated = self.genome_generator.generate_from_crossbreeding(parents, children_count=max(1, children))
        else:
            count = int(payload.get("count", 10))
            generated = self.genome_generator.generate_random(count=max(1, count))
        return {"generated": generated, "count": len(generated)}

    def _backtest(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # Uses Strategy Lab hook when available.
        if self.strategy_lab is not None and hasattr(self.strategy_lab, "run_experiment"):
            gen = int(payload.get("generate_count", 4))
            variants = int(payload.get("variants_per_base", 2))
            periods = int(payload.get("periods", 260))
            result = self.strategy_lab.run_experiment(
                generate_count=max(1, gen),
                variants_per_base=max(1, variants),
                periods=max(120, periods),
            )
            return {"backtest_result": result}
        return {"backtest_result": {"note": "strategy_lab_unavailable"}}

    def _strategy_evaluation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        genomes = payload.get("genomes", [])
        if self.genome_evaluator is None:
            return {"reports": []}
        reports = self.genome_evaluator.evaluate_genomes(genomes)
        return {"reports": reports, "count": len(reports)}

    def _shadow_analysis(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        sid = str(payload.get("strategy_id", "")).strip()
        engine = self.shadow_trading_engine
        if not engine or not sid:
            return {"metrics": {}, "strategy_id": sid}
        tracker = getattr(engine, "performance_tracker", None)
        if tracker is None:
            return {"metrics": {}, "strategy_id": sid}
        metrics = tracker.metrics(sid)
        return {"metrics": metrics, "strategy_id": sid}

    def health(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "status": self.status,
            "tasks_processed": self.tasks_processed,
            "tasks_failed": self.tasks_failed,
            "supports": sorted(self.SUPPORTED_TASKS),
        }


"""Genome evaluator using backtest, shadow, and live-feedback signals."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional


class GenomeEvaluator:
    """Evaluates candidate genomes and emits normalized reports.

    ResearchMemoryLayer integration
    --------------------------------
    Pass research_memory=router.research_memory to archive every evaluation
    into PerformanceArchive and update AlphaMemoryStore with live metrics.
    Pass genome_library=lib to write fitness scores back to GenomeRecord via
    library.update_fitness() after each evaluation.
    Both parameters are optional — omitting them has no effect on the algorithm.
    """

    def __init__(
        self,
        strategy_lab             = None,
        shadow_trading_engine    = None,
        adaptive_learning_engine = None,
        meta_strategy_brain      = None,
        research_memory          = None,
        genome_library           = None,
        **kwargs,
    ):
        self.strategy_lab             = strategy_lab
        self.shadow_trading_engine    = shadow_trading_engine
        self.adaptive_learning_engine = adaptive_learning_engine
        self.meta_strategy_brain      = meta_strategy_brain
        self.last_reports: List[Dict] = []

        self._library = genome_library
        self._bridge  = None
        if research_memory is not None:
            self._wire_bridge(research_memory)

    def set_research_memory(self, research_memory, genome_library=None) -> None:
        """Late injection of ResearchMemoryLayer."""
        self._wire_bridge(research_memory)
        if genome_library is not None:
            self._library = genome_library

    def _wire_bridge(self, rm) -> None:
        try:
            from quant_ecosystem.alpha_genome._memory_bridge import GenomeMemoryBridge
            self._bridge = GenomeMemoryBridge(research_memory=rm)
        except Exception:
            pass

    def evaluate_genomes(self, genomes: Iterable[Dict]) -> List[Dict]:
        reports = []
        for genome in list(genomes or []):
            report = self._evaluate_one(genome)
            reports.append(report)
        self.last_reports = reports
        return reports

    def _evaluate_one(self, genome: Dict) -> Dict:
        gid    = str(genome.get("genome_id", "unknown"))
        back   = self._backtest_score(genome)
        shadow = self._shadow_score(gid)
        live   = self._live_feedback_score(gid)

        sharpe   = (back.get("sharpe",        0.0) * 0.5) + (shadow.get("sharpe",        0.0) * 0.3) + (live.get("sharpe",        0.0) * 0.2)
        drawdown = (back.get("drawdown",       0.0) * 0.5) + (shadow.get("drawdown",       0.0) * 0.3) + (live.get("drawdown",       0.0) * 0.2)
        win_rate = (back.get("win_rate",       0.0) * 0.6) + (shadow.get("win_rate",       0.0) * 0.25) + (live.get("win_rate",      0.0) * 0.15)
        pf       = (back.get("profit_factor",  1.0) * 0.5) + (shadow.get("profit_factor",  1.0) * 0.3) + (live.get("profit_factor",  1.0) * 0.2)

        fitness = self._fitness_score(sharpe=sharpe, drawdown=drawdown, win_rate=win_rate, profit_factor=pf)
        out = {
            "genome_id":     gid,
            "fitness_score": round(fitness,   6),
            "sharpe":        round(sharpe,    6),
            "drawdown":      round(drawdown,  6),
            "win_rate":      round(win_rate,  6),
            "profit_factor": round(pf,        6),
            "trade_count":   int(back.get("trade_count", 0)),
            "components":    {"backtest": back, "shadow": shadow, "live_feedback": live},
        }
        self._publish(gid, out)

        # --- ResearchMemoryLayer hook: archive evaluation + update fitness ---
        if self._bridge:
            self._bridge.record_evaluation(
                genome_id = gid,
                metrics   = {
                    "sharpe":        round(sharpe,   6),
                    "drawdown":      round(drawdown, 6),
                    "profit_factor": round(pf,       6),
                    "win_rate":      round(win_rate, 6),
                    "fitness_score": round(fitness,  6),
                    "trade_count":   out["trade_count"],
                },
                genome = genome,
            )
        # Write fitness back to GenomeLibrary
        if self._library:
            self._library.update_fitness(
                genome_id     = gid,
                fitness_score = round(fitness,  6),
                sharpe        = round(sharpe,   6),
                drawdown      = round(drawdown, 6),
                profit_factor = round(pf,       6),
                win_rate      = round(win_rate, 6),
                trade_count   = out["trade_count"],
            )

        return out

    def _backtest_score(self, genome: Dict) -> Dict:
        # If strategy lab has a compatible score API, use it; otherwise use deterministic proxy from genes.
        lab = self.strategy_lab
        if lab and hasattr(lab, "evaluate_genome"):
            try:
                payload = lab.evaluate_genome(genome)  # optional integration hook
                if isinstance(payload, dict):
                    return self._normalize_metrics(payload)
            except Exception:
                pass

        signal = dict(genome.get("signal_gene", {}) or {})
        risk = dict(genome.get("risk_gene", {}) or {})
        exec_gene = dict(genome.get("execution_gene", {}) or {})
        threshold = self._f(signal.get("threshold", 0.6))
        risk_pct = self._f(risk.get("risk_pct", 1.0))
        slip_limit = self._f(exec_gene.get("slippage_bps_limit", 10.0))
        sharpe = max(-1.5, 2.4 - abs(threshold - 0.65) * 6.0 - (risk_pct * 0.25))
        drawdown = max(0.5, (risk_pct * 5.5) + (slip_limit * 0.06))
        win_rate = min(0.95, max(0.2, 0.5 + (0.65 - abs(threshold - 0.65)) * 0.45))
        pf = min(3.5, max(0.6, 1.0 + (sharpe * 0.35) - (drawdown * 0.03)))
        return {
            "sharpe": round(sharpe, 6),
            "drawdown": round(drawdown, 6),
            "win_rate": round(win_rate, 6),
            "profit_factor": round(pf, 6),
        }

    def _shadow_score(self, genome_id: str) -> Dict:
        engine = self.shadow_trading_engine
        if not engine or not hasattr(engine, "performance_tracker"):
            return {"sharpe": 0.0, "drawdown": 0.0, "win_rate": 0.0, "profit_factor": 1.0}
        try:
            m = engine.performance_tracker.metrics(genome_id)
            if not m:
                return {"sharpe": 0.0, "drawdown": 0.0, "win_rate": 0.0, "profit_factor": 1.0}
            return self._normalize_metrics(m)
        except Exception:
            return {"sharpe": 0.0, "drawdown": 0.0, "win_rate": 0.0, "profit_factor": 1.0}

    def _live_feedback_score(self, genome_id: str) -> Dict:
        eng = self.adaptive_learning_engine
        if not eng:
            return {"sharpe": 0.0, "drawdown": 0.0, "win_rate": 0.0, "profit_factor": 1.0}
        payload = dict(getattr(eng, "last_updates", {}) or {})
        updates = list(payload.get("updates", []) or [])
        row = next((item for item in updates if str(item.get("strategy_id", "")) == genome_id), None)
        if not row:
            return {"sharpe": 0.0, "drawdown": 0.0, "win_rate": 0.0, "profit_factor": 1.0}
        regime_perf = dict(row.get("regime_performance", {}) or {})
        return self._normalize_metrics(regime_perf)

    def _publish(self, genome_id: str, report: Dict) -> None:
        brain = self.meta_strategy_brain
        if brain is not None:
            try:
                bag = dict(getattr(brain, "last_genome_reports", {}) or {})
                bag[genome_id] = report
                setattr(brain, "last_genome_reports", bag)
            except Exception:
                pass

    def _fitness_score(self, sharpe: float, drawdown: float, win_rate: float, profit_factor: float) -> float:
        return (0.35 * sharpe) + (0.25 * profit_factor) + (0.25 * win_rate) - (0.15 * max(0.0, drawdown))

    def _normalize_metrics(self, payload: Dict) -> Dict:
        return {
            "sharpe": self._f(payload.get("sharpe", payload.get("sharpe_ratio", 0.0))),
            "drawdown": self._f(payload.get("drawdown", payload.get("max_drawdown", 0.0))),
            "win_rate": self._f(payload.get("win_rate", 0.0)),
            "profit_factor": self._f(payload.get("profit_factor", 1.0)),
        }

    def _f(self, value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0


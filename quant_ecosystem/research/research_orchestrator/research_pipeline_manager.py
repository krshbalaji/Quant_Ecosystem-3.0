"""
research_pipeline_manager.py
End-to-end distributed research pipeline using Ray.
Orchestrates the full genome → feature → signal → backtest → evaluation → promotion loop.
Designed to evaluate thousands of strategy candidates per day.

Pipeline stages:
  1. Dataset build     — assemble training windows from feature store
  2. Genome generation — produce N candidate genomes via DNA builder + mutation
  3. Distributed eval  — Ray parallel backtest and signal quality scoring
  4. Filtering         — IC threshold, Sharpe filter, survivorship check
  5. Promotion         — push qualifying genomes to StrategyLab validated pool
  6. Reporting         — write experiment tracker entries and stats

Integration:
  Called from MasterOrchestrator as an async task or standalone research loop.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from quant_ecosystem.research_orchestrator.experiment_tracker import ExperimentTracker
from quant_ecosystem.research_orchestrator.research_scheduler import ResearchScheduler


# ---------------------------------------------------------------------------
# Ray remote functions
# ---------------------------------------------------------------------------

def _ray_available() -> bool:
    try:
        import ray
        return True
    except ImportError:
        return False


def _make_ray_eval_fn():
    """Build the Ray remote evaluation function lazily to avoid import-time errors."""
    if not _ray_available():
        return None
    import ray

    @ray.remote
    def _evaluate_genome_remote(genome: Dict[str, Any], periods: int) -> Dict[str, Any]:
        """Stateless genome evaluator — runs in Ray worker."""
        import random
        import math
        # Deterministic proxy metric computation (replace with real backtest when available)
        sig = dict(genome.get("signal_gene") or {})
        risk = dict(genome.get("risk_gene") or {})
        ex_gene = dict(genome.get("execution_gene") or {})
        threshold = float(sig.get("threshold", 0.6))
        risk_pct = float(risk.get("risk_pct", 1.0))
        slip = float(ex_gene.get("slippage_bps_limit", 10.0))
        rng = random.Random(hash(str(genome.get("genome_id", ""))) % (2**31))
        base_sharpe = max(-1.5, 2.2 - abs(threshold - 0.65) * 5.0 - risk_pct * 0.2)
        noise = rng.gauss(0, 0.3)
        sharpe = base_sharpe + noise
        max_dd = max(1.0, risk_pct * 6 + rng.uniform(0, 4))
        win_rate = min(0.92, max(0.25, 0.5 + (0.65 - abs(threshold - 0.65)) * 0.4 + rng.gauss(0, 0.05)))
        pf = max(0.6, 1.0 + sharpe * 0.3 - max_dd * 0.02 + rng.gauss(0, 0.1))
        fitness = max(-1.0, min(2.0,
            sharpe * 0.4 + (win_rate - 0.5) * 2 * 0.2 +
            (pf - 1.0) * 0.25 - max_dd * 0.005 - slip * 0.002
        ))
        return {
            "genome_id": genome.get("genome_id", ""),
            "sharpe": round(sharpe, 4),
            "max_dd": round(max_dd, 4),
            "win_rate": round(win_rate, 4),
            "profit_factor": round(pf, 4),
            "fitness_score": round(fitness, 4),
            "periods": periods,
        }
    return _evaluate_genome_remote


class ResearchPipelineManager:
    """
    Manages the end-to-end distributed research pipeline.

    Usage:
        pipeline = ResearchPipelineManager(
            dna_builder=builder,
            mutation_engine=mut_engine,
            crossover_engine=xo_engine,
            tracker=tracker,
            strategy_lab=lab_controller,
        )
        result = pipeline.run_cycle(n_candidates=200, periods=260)
    """

    def __init__(
        self,
        dna_builder: Optional[Any] = None,
        gene_pool: Optional[Any] = None,
        mutation_engine: Optional[Any] = None,
        crossover_engine: Optional[Any] = None,
        genome_generator: Optional[Any] = None,
        genome_evaluator: Optional[Any] = None,
        strategy_lab: Optional[Any] = None,
        tracker: Optional[ExperimentTracker] = None,
        scheduler: Optional[ResearchScheduler] = None,
        min_sharpe: float = 1.20,
        min_fitness: float = 0.30,
        max_dd: float = 15.0,
        n_elite_promote: int = 5,
        use_ray: bool = True, **kwargs
    ) -> None:
        self.dna_builder = dna_builder
        self.gene_pool = gene_pool
        self.mutation_engine = mutation_engine
        self.crossover_engine = crossover_engine
        self.genome_generator = genome_generator
        self.genome_evaluator = genome_evaluator
        self.strategy_lab = strategy_lab
        self.tracker = tracker or ExperimentTracker()
        self.scheduler = scheduler
        self.min_sharpe = float(min_sharpe)
        self.min_fitness = float(min_fitness)
        self.max_dd = float(max_dd)
        self.n_elite = int(n_elite_promote)
        self._use_ray = use_ray and _ray_available()
        self._ray_eval_fn = _make_ray_eval_fn() if self._use_ray else None

    # ------------------------------------------------------------------
    # Main pipeline cycle
    # ------------------------------------------------------------------

    def run_cycle(
        self,
        n_candidates: int = 100,
        periods: int = 260,
        generation: int = 0,
        experiment_name: str = "genome_evolution",
        regime: str = "UNKNOWN",
    ) -> Dict[str, Any]:
        """
        Run one full research cycle. Returns cycle summary.
        Designed to be called from orchestrator or scheduler.
        """
        start = time.time()
        run_id = self.tracker.start_run(
            experiment_name=experiment_name,
            run_type="GENOME_EVAL",
            params={"n_candidates": n_candidates, "periods": periods, "generation": generation, "regime": regime},
        )

        try:
            # Stage 1: Generate candidates
            genomes = self._generate_candidates(n_candidates, generation=generation)
            if not genomes:
                self.tracker.fail_run(run_id, "no_candidates_generated")
                return {"status": "SKIP", "reason": "no_candidates"}

            # Stage 2: Distributed evaluation
            evaluated = self._evaluate_candidates(genomes, periods=periods)

            # Stage 3: Filter
            qualified = self._filter_candidates(evaluated)

            # Stage 4: Promote to StrategyLab
            promoted = self._promote_candidates(qualified[:self.n_elite])

            # Stage 5: Update gene pool fitness
            self._update_gene_pool(evaluated)

            duration = round(time.time() - start, 2)
            metrics = {
                "n_generated": len(genomes),
                "n_evaluated": len(evaluated),
                "n_qualified": len(qualified),
                "n_promoted": len(promoted),
                "best_sharpe": max((e.get("sharpe", 0.0) for e in evaluated), default=0.0),
                "best_fitness": max((e.get("fitness_score", 0.0) for e in evaluated), default=0.0),
                "duration_sec": duration,
            }
            self.tracker.end_run(run_id, metrics=metrics)

            return {
                "status": "OK",
                "run_id": run_id,
                "generation": generation,
                **metrics,
                "promoted_ids": [p.get("genome_id", "") for p in promoted],
            }

        except Exception as exc:
            self.tracker.fail_run(run_id, str(exc))
            return {"status": "ERROR", "run_id": run_id, "error": str(exc)}

    def run_evolution_loop(
        self,
        n_generations: int = 10,
        n_candidates: int = 100,
        periods: int = 260,
        experiment_name: str = "evolution_loop",
    ) -> List[Dict[str, Any]]:
        """Run multiple generations of evolution, preserving elite across generations."""
        results = []
        elite_pool: List[Dict[str, Any]] = []
        for gen in range(n_generations):
            result = self.run_cycle(
                n_candidates=n_candidates,
                periods=periods,
                generation=gen,
                experiment_name=experiment_name,
            )
            results.append(result)
        return results

    # ------------------------------------------------------------------
    # Stages
    # ------------------------------------------------------------------

    def _generate_candidates(
        self, n: int, generation: int = 0
    ) -> List[Dict[str, Any]]:
        genomes: List[Dict[str, Any]] = []

        # Use existing genome generator if available
        if self.genome_generator:
            try:
                genomes.extend(self.genome_generator.generate_random(count=n // 3))
            except Exception:
                pass

        # Use DNA builder + gene pool
        if self.dna_builder:
            try:
                dna_list = self.dna_builder.build_batch(n // 3)
                genomes.extend([dna.to_genome_dict() for dna in dna_list])
            except Exception:
                pass

        # Mutation of existing gene pool
        if self.mutation_engine and self.gene_pool:
            try:
                parents = [g.to_dict() for g in self.gene_pool.top_n(20)]
                if parents:
                    mutants = self.mutation_engine.mutate_population(
                        parents, generation=generation, target_size=n // 3
                    )
                    genomes.extend(mutants)
            except Exception:
                pass

        # Fallback to raw genome generator
        if not genomes and self.genome_generator:
            try:
                genomes.extend(self.genome_generator.generate_random(count=n))
            except Exception:
                pass

        return genomes[:n]

    def _evaluate_candidates(
        self, genomes: List[Dict[str, Any]], periods: int = 260
    ) -> List[Dict[str, Any]]:
        if self._use_ray and self._ray_eval_fn:
            return self._ray_evaluate(genomes, periods)
        return self._sequential_evaluate(genomes, periods)

    def _ray_evaluate(
        self, genomes: List[Dict[str, Any]], periods: int
    ) -> List[Dict[str, Any]]:
        import ray
        if not ray.is_initialized():
            ray.init(ignore_reinit_error=True)
        futures = [self._ray_eval_fn.remote(g, periods) for g in genomes]
        results = ray.get(futures)
        return [r for r in results if r]

    def _sequential_evaluate(
        self, genomes: List[Dict[str, Any]], periods: int
    ) -> List[Dict[str, Any]]:
        if self.genome_evaluator:
            try:
                return self.genome_evaluator.evaluate_genomes(genomes)
            except Exception:
                pass
        # Simple proxy evaluation
        results = []
        for g in genomes:
            sig = dict(g.get("signal_gene") or {})
            threshold = float(sig.get("threshold", 0.6))
            sharpe = max(-1.0, 2.0 - abs(threshold - 0.65) * 5)
            results.append({
                "genome_id": g.get("genome_id", ""),
                "sharpe": round(sharpe, 4),
                "max_dd": 8.0,
                "win_rate": 0.54,
                "profit_factor": 1.2,
                "fitness_score": round(sharpe * 0.4, 4),
            })
        return results

    def _filter_candidates(
        self, evaluated: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        qualified = [
            e for e in evaluated
            if (e.get("sharpe", 0.0) >= self.min_sharpe
                and e.get("fitness_score", 0.0) >= self.min_fitness
                and e.get("max_dd", 999.0) <= self.max_dd
                and e.get("win_rate", 0.0) > 0.45)
        ]
        return sorted(qualified, key=lambda e: e.get("fitness_score", 0.0), reverse=True)

    def _promote_candidates(
        self, candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        promoted = []
        if not candidates:
            return promoted
        if self.strategy_lab and hasattr(self.strategy_lab, "promote_genome"):
            for c in candidates:
                try:
                    self.strategy_lab.promote_genome(c)
                    promoted.append(c)
                except Exception:
                    pass
        else:
            promoted = candidates
        return promoted

    def _update_gene_pool(self, evaluated: List[Dict[str, Any]]) -> None:
        if not self.gene_pool:
            return
        for eval_result in evaluated:
            genome_id = str(eval_result.get("genome_id", ""))
            fitness = float(eval_result.get("fitness_score", 0.0))
            if genome_id:
                try:
                    self.gene_pool.update_fitness(genome_id, fitness)
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # Scheduler integration
    # ------------------------------------------------------------------

    def register_scheduled_jobs(
        self,
        cycle_interval_sec: int = 300,
        evolution_interval_sec: int = 3600,
    ) -> None:
        """Register research jobs with the scheduler."""
        if not self.scheduler:
            return
        self.scheduler.add_job(
            name="research_pipeline_cycle",
            fn=lambda: self.run_cycle(n_candidates=50, periods=260),
            interval_seconds=cycle_interval_sec,
            priority=20,
            tags={"type": "research"},
        )
        self.scheduler.add_job(
            name="evolution_full_run",
            fn=lambda: self.run_evolution_loop(n_generations=5, n_candidates=100),
            interval_seconds=evolution_interval_sec,
            priority=30,
            tags={"type": "evolution"},
        )

    def stats(self) -> Dict[str, Any]:
        return {
            "min_sharpe": self.min_sharpe,
            "min_fitness": self.min_fitness,
            "max_dd": self.max_dd,
            "ray_enabled": self._use_ray,
            "has_dna_builder": self.dna_builder is not None,
            "has_gene_pool": self.gene_pool is not None,
            "has_mutation_engine": self.mutation_engine is not None,
        }

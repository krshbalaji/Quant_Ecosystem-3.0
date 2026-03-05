"""
alpha_mutation_engine.py
Population-level mutation engine for the alpha genome pipeline.
Wraps the low-level GenomeMutator with evolutionary algorithms:
  - Elite preservation
  - Tournament selection
  - Adaptive mutation rate (annealing based on fitness plateau)
  - Directional mutation (bias toward higher-fitness parameter regions)
"""

from __future__ import annotations

import copy
import math
import random
from typing import Any, Dict, List, Optional, Tuple

from quant_ecosystem.alpha_genome.genome_mutator import GenomeMutator
from quant_ecosystem.alpha_genome.alpha_gene_pool import AlphaGenePool


class PopulationStats:
    """Tracks population fitness statistics for adaptive mutation."""

    def __init__(self, window: int = 10) -> None:
        self._history: List[float] = []
        self._window = window

    def record(self, mean_fitness: float) -> None:
        self._history.append(mean_fitness)
        if len(self._history) > self._window * 3:
            self._history = self._history[-(self._window * 3):]

    def improvement_rate(self) -> float:
        """Return fractional improvement over last window. 0 = plateau."""
        if len(self._history) < self._window:
            return 1.0
        recent = self._history[-self._window:]
        older = self._history[-self._window * 2 : -self._window]
        if not older:
            return 1.0
        old_mean = sum(older) / len(older)
        new_mean = sum(recent) / len(recent)
        if old_mean == 0:
            return 1.0
        return (new_mean - old_mean) / abs(old_mean)

    def is_plateau(self, threshold: float = 0.01) -> bool:
        return abs(self.improvement_rate()) < threshold


class AlphaMutationEngine:
    """
    Evolutionary mutation engine that operates on genome populations.

    Usage:
        engine = AlphaMutationEngine(gene_pool=gene_pool)
        mutants = engine.mutate_population(parent_genomes, generation=5)
    """

    def __init__(
        self,
        gene_pool: Optional[AlphaGenePool] = None,
        base_mutation_rate: float = 0.25,
        elite_pct: float = 0.10,
        tournament_size: int = 4,
        max_mutation_rate: float = 0.60,
        min_mutation_rate: float = 0.10,
    ) -> None:
        self.gene_pool = gene_pool
        self._base_rate = float(base_mutation_rate)
        self._elite_pct = float(elite_pct)
        self._tournament_size = max(2, int(tournament_size))
        self._max_rate = float(max_mutation_rate)
        self._min_rate = float(min_mutation_rate)
        self._mutator = GenomeMutator(mutation_rate=base_mutation_rate)
        self._stats = PopulationStats()
        self._current_rate = base_mutation_rate

    # ------------------------------------------------------------------
    # Main API
    # ------------------------------------------------------------------

    def mutate_population(
        self,
        population: List[Dict[str, Any]],
        generation: int = 0,
        target_size: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Evolve a population by one generation.
        Returns a new population of the same size (or target_size).
        """
        if not population:
            return []

        n = target_size or len(population)
        population = [dict(g) for g in population]

        # Compute fitness for sorting (use genome's stored fitness if present)
        ranked = sorted(
            population,
            key=lambda g: float(g.get("fitness_score", g.get("fitness", 0.0))),
            reverse=True,
        )

        # Adaptive mutation rate
        mean_fitness = sum(
            float(g.get("fitness_score", g.get("fitness", 0.0))) for g in ranked
        ) / len(ranked)
        self._stats.record(mean_fitness)
        self._adapt_rate()

        # Elite preservation
        n_elite = max(1, int(n * self._elite_pct))
        elite = ranked[:n_elite]

        # Fill remainder via tournament selection + mutation
        offspring: List[Dict[str, Any]] = list(elite)
        while len(offspring) < n:
            parent = self._tournament_select(ranked)
            child = self._mutate_one(parent, generation=generation)
            offspring.append(child)

        return offspring[:n]

    def mutate_one(self, genome: Dict[str, Any], generation: int = 0) -> Dict[str, Any]:
        """Mutate a single genome and return the child."""
        return self._mutate_one(genome, generation=generation)

    def directional_mutate(
        self,
        genome: Dict[str, Any],
        gradient: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        Apply directional mutation biased toward a fitness gradient.
        gradient: mapping of param_path → direction (+1/-1) with magnitude.
        e.g. {"signal_gene.threshold": +0.3} nudges threshold upward.
        """
        child = copy.deepcopy(genome)
        for path, direction in gradient.items():
            parts = path.split(".")
            ref = child
            for p in parts[:-1]:
                if not isinstance(ref, dict):
                    break
                ref = ref.setdefault(p, {})
            key = parts[-1]
            if isinstance(ref, dict) and key in ref:
                val = ref[key]
                if isinstance(val, (int, float)):
                    jitter = abs(val) * self._current_rate * abs(direction)
                    ref[key] = round(val + math.copysign(jitter, direction), 8)
        return child

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _mutate_one(self, genome: Dict[str, Any], generation: int = 0) -> Dict[str, Any]:
        self._mutator.mutation_rate = self._current_rate
        child = self._mutator.mutate(genome)
        child["metadata"] = dict(child.get("metadata") or {})
        child["metadata"]["generation"] = generation
        child["metadata"]["mutation_rate_used"] = round(self._current_rate, 4)

        # Optionally inject a random gene from pool for diversity
        if self.gene_pool and random.random() < 0.10:
            self._inject_random_gene(child)

        return child

    def _tournament_select(self, ranked: List[Dict[str, Any]]) -> Dict[str, Any]:
        candidates = random.sample(ranked, min(self._tournament_size, len(ranked)))
        return max(
            candidates,
            key=lambda g: float(g.get("fitness_score", g.get("fitness", 0.0))),
        )

    def _adapt_rate(self) -> None:
        """Anneal mutation rate: increase on plateau, decrease on improvement."""
        if self._stats.is_plateau(threshold=0.005):
            # Plateau detected — increase exploration
            self._current_rate = min(self._max_rate, self._current_rate * 1.15)
        else:
            # Good progress — reduce mutation to exploit
            self._current_rate = max(self._min_rate, self._current_rate * 0.92)

    def _inject_random_gene(self, genome: Dict[str, Any]) -> None:
        """Replace one random gene slot with a fresh pool gene for diversity."""
        gene_slots = [
            "market_filter_gene", "signal_gene", "entry_gene",
            "exit_gene", "risk_gene", "execution_gene",
        ]
        slot = random.choice(gene_slots)
        sampled = self.gene_pool.sample(n=1)
        if sampled:
            g = sampled[0]
            genome[slot] = {"gene_type": g.gene_type, "family": g.family, **g.params}

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        return {
            "current_mutation_rate": round(self._current_rate, 4),
            "base_mutation_rate": round(self._base_rate, 4),
            "is_plateau": self._stats.is_plateau(),
            "improvement_rate": round(self._stats.improvement_rate(), 6),
        }

    def get_elite(
        self, population: List[Dict[str, Any]], top_n: int = 10
    ) -> List[Dict[str, Any]]:
        """Return top N genomes by fitness from a population."""
        return sorted(
            population,
            key=lambda g: float(g.get("fitness_score", g.get("fitness", 0.0))),
            reverse=True,
        )[:top_n]

    def diversity_score(self, population: List[Dict[str, Any]]) -> float:
        """Approximate population diversity via unique genome-id count / total."""
        if not population:
            return 0.0
        unique = len({str(g.get("genome_id", "")) for g in population})
        return unique / len(population)

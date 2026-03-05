"""
alpha_crossover_engine.py
Population-level crossover engine for the alpha genome pipeline.
Implements multiple crossover strategies on top of GenomeCrossbreeder:
  - Uniform crossover       (each gene randomly from either parent)
  - K-point crossover       (gene sequence split at K points)
  - Family-aware crossover  (prefer genes from the same strategy family)
  - Blend crossover         (blend numeric params between parents)
  - Fitness-weighted        (fitter parent donates more genes)
"""

from __future__ import annotations

import copy
import random
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from quant_ecosystem.alpha_genome.genome_crossbreeder import GenomeCrossbreeder


_GENE_KEYS = [
    "market_filter_gene",
    "signal_gene",
    "entry_gene",
    "exit_gene",
    "risk_gene",
    "execution_gene",
]


class AlphaCrossoverEngine:
    """
    Population-level crossover producing offspring from parent pairs.

    Usage:
        engine = AlphaCrossoverEngine()
        children = engine.crossover_population(parent_pool, n_offspring=50)
        child = engine.crossover_pair(parent_a, parent_b, mode="blend")
    """

    def __init__(
        self,
        k_points: int = 2,
        blend_alpha: float = 0.3,
        fitness_bias: bool = True,
    ) -> None:
        self._k = max(1, int(k_points))
        self._blend_alpha = float(blend_alpha)
        self._fitness_bias = fitness_bias
        self._base_crossbreeder = GenomeCrossbreeder()

    # ------------------------------------------------------------------
    # Population-level API
    # ------------------------------------------------------------------

    def crossover_population(
        self,
        parents: List[Dict[str, Any]],
        n_offspring: int = 50,
        mode: str = "uniform",
    ) -> List[Dict[str, Any]]:
        """
        Produce n_offspring from a parent pool.
        Mode: "uniform" | "kpoint" | "blend" | "family" | "weighted"
        """
        if len(parents) < 2:
            return [copy.deepcopy(p) for p in parents[:n_offspring]]

        # Rank parents by fitness (for fitness-weighted selection)
        ranked = sorted(
            parents,
            key=lambda g: float(g.get("fitness_score", g.get("fitness", 0.0))),
            reverse=True,
        )

        offspring: List[Dict[str, Any]] = []
        while len(offspring) < n_offspring:
            pa, pb = self._select_pair(ranked)
            child = self.crossover_pair(pa, pb, mode=mode)
            offspring.append(child)

        return offspring

    def crossover_pair(
        self,
        parent_a: Dict[str, Any],
        parent_b: Dict[str, Any],
        mode: str = "uniform",
    ) -> Dict[str, Any]:
        """
        Cross two parent genomes. Returns one child.
        Mode: "uniform" | "kpoint" | "blend" | "family" | "weighted"
        """
        m = str(mode).lower()
        if m == "kpoint":
            return self._kpoint_crossover(parent_a, parent_b)
        if m == "blend":
            return self._blend_crossover(parent_a, parent_b)
        if m == "family":
            return self._family_crossover(parent_a, parent_b)
        if m == "weighted":
            return self._fitness_weighted_crossover(parent_a, parent_b)
        # Default: uniform crossover via base crossbreeder
        return self._base_crossbreeder.crossbreed(parent_a, parent_b)

    # ------------------------------------------------------------------
    # Crossover implementations
    # ------------------------------------------------------------------

    def _kpoint_crossover(
        self, pa: Dict[str, Any], pb: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Split gene sequence at k random points and alternate between parents."""
        keys = list(_GENE_KEYS)
        k = min(self._k, len(keys) - 1)
        points = sorted(random.sample(range(1, len(keys)), k))

        child: Dict[str, Any] = {"metadata": {}}
        current_parent = random.choice([pa, pb])
        other = pb if current_parent is pa else pa
        prev = 0
        for point in points + [len(keys)]:
            for key in keys[prev:point]:
                gene = copy.deepcopy(current_parent.get(key) or other.get(key) or {})
                child[key] = gene
            current_parent, other = other, current_parent
            prev = point

        self._stamp_child(child, pa, pb, method="kpoint")
        return child

    def _blend_crossover(
        self, pa: Dict[str, Any], pb: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Blend numeric parameters between parents; non-numerics from random parent."""
        alpha = self._blend_alpha
        child: Dict[str, Any] = {"metadata": {}}

        for key in _GENE_KEYS:
            ga = dict(pa.get(key) or {})
            gb = dict(pb.get(key) or {})
            if not ga and not gb:
                continue

            # Random parent provides the template; blend numeric fields
            template = copy.deepcopy(ga if random.random() < 0.5 else gb)
            blended = {}
            for field, val in template.items():
                val_a = ga.get(field, val)
                val_b = gb.get(field, val)
                if isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
                    # BLX-α blend
                    lo, hi = min(val_a, val_b), max(val_a, val_b)
                    extent = (hi - lo) * alpha
                    blended[field] = round(
                        random.uniform(lo - extent, hi + extent), 6
                    )
                else:
                    blended[field] = val_a if random.random() < 0.5 else val_b
            child[key] = blended

        self._stamp_child(child, pa, pb, method="blend")
        return child

    def _family_crossover(
        self, pa: Dict[str, Any], pb: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prefer genes from the parent whose signal family matches slot convention."""
        from quant_ecosystem.alpha_genome.alpha_dna_builder import _SLOT_FAMILY_MAP

        child: Dict[str, Any] = {"metadata": {}}
        for key in _GENE_KEYS:
            ga = pa.get(key) or {}
            gb = pb.get(key) or {}
            preferred_families = _SLOT_FAMILY_MAP.get(key, [])
            family_a = str(ga.get("family", "")).lower()
            family_b = str(gb.get("family", "")).lower()

            a_match = family_a in preferred_families
            b_match = family_b in preferred_families

            if a_match and not b_match:
                source = ga
            elif b_match and not a_match:
                source = gb
            else:
                source = ga if random.random() < 0.5 else gb
            child[key] = copy.deepcopy(source)

        self._stamp_child(child, pa, pb, method="family")
        return child

    def _fitness_weighted_crossover(
        self, pa: Dict[str, Any], pb: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fitter parent donates more genes (proportional to fitness ratio)."""
        fit_a = max(0.0, float(pa.get("fitness_score", pa.get("fitness", 0.0))))
        fit_b = max(0.0, float(pb.get("fitness_score", pb.get("fitness", 0.0))))
        total = fit_a + fit_b
        p_a = fit_a / total if total > 0 else 0.5

        child: Dict[str, Any] = {"metadata": {}}
        for key in _GENE_KEYS:
            source = pa if random.random() < p_a else pb
            other = pb if source is pa else pa
            gene = copy.deepcopy(source.get(key) or other.get(key) or {})
            child[key] = gene

        self._stamp_child(child, pa, pb, method="weighted")
        return child

    # ------------------------------------------------------------------
    # Pair selection
    # ------------------------------------------------------------------

    def _select_pair(
        self, ranked: List[Dict[str, Any]]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Select two distinct parents. With fitness bias, prefer higher-ranked."""
        n = len(ranked)
        if self._fitness_bias:
            # Rank-proportional weights: rank 1 gets weight n, rank n gets weight 1
            weights = list(range(n, 0, -1))
            pa, pb = random.choices(ranked, weights=weights, k=2)
            if pa is pb and n > 1:
                pb = random.choice([g for g in ranked if g is not pa])
        else:
            pa, pb = random.sample(ranked, 2)
        return pa, pb

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _stamp_child(
        child: Dict[str, Any],
        pa: Dict[str, Any],
        pb: Dict[str, Any],
        method: str,
    ) -> None:
        aid = str(pa.get("genome_id", "A"))
        bid = str(pb.get("genome_id", "B"))
        child["genome_id"] = f"{aid}X{bid}_{random.randint(1000, 9999)}"
        meta = child.setdefault("metadata", {})
        meta["crossbred_from"] = [aid, bid]
        meta["crossover_method"] = method
        meta["crossbred_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    def diversity_matrix(
        self, population: List[Dict[str, Any]]
    ) -> List[Tuple[str, str, float]]:
        """
        Compute pairwise diversity as fraction of differing gene families.
        Returns list of (id_a, id_b, diversity_score).
        Useful for selecting mating pairs that maximise offspring diversity.
        """
        results = []
        for i in range(len(population)):
            for j in range(i + 1, len(population)):
                ga, gb = population[i], population[j]
                diffs = sum(
                    1 for k in _GENE_KEYS
                    if str((ga.get(k) or {}).get("family", "")) !=
                       str((gb.get(k) or {}).get("family", ""))
                )
                score = diffs / len(_GENE_KEYS)
                results.append((
                    str(ga.get("genome_id", i)),
                    str(gb.get("genome_id", j)),
                    round(score, 4),
                ))
        return results

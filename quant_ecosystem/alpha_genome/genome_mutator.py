"""Genome mutator for Alpha Genome Engine."""

from __future__ import annotations

import copy
import random
from datetime import datetime
from typing import Dict, Optional, Tuple


class GenomeMutator:
    """Applies bounded mutations to genome genes.

    ResearchMemoryLayer integration
    --------------------------------
    Pass research_memory=router.research_memory to record every parent→child
    mutation in AlphaMemoryStore and StrategyGenealogy.
    The hook fires *after* the child genome is fully constructed — the core
    mutation algorithm is unchanged.
    """

    def __init__(
        self,
        mutation_rate:      float = 0.25,
        numeric_jitter_pct: float = 0.20,
        research_memory            = None,
        **kwargs,
    ):
        self.mutation_rate      = float(mutation_rate)
        self.numeric_jitter_pct = float(numeric_jitter_pct)
        self._bridge = None
        if research_memory is not None:
            self._wire_bridge(research_memory)

    def set_research_memory(self, research_memory) -> None:
        """Late injection of ResearchMemoryLayer."""
        self._wire_bridge(research_memory)

    def _wire_bridge(self, rm) -> None:
        try:
            from quant_ecosystem.alpha_genome._memory_bridge import GenomeMemoryBridge
            self._bridge = GenomeMemoryBridge(research_memory=rm)
        except Exception:
            pass

    def mutate(self, genome: Dict, seed: int | None = None) -> Dict:
        rng = random.Random(seed)
        child = copy.deepcopy(dict(genome or {}))
        child.setdefault("metadata", {})
        for gene_key in (
            "market_filter_gene",
            "signal_gene",
            "entry_gene",
            "exit_gene",
            "risk_gene",
            "execution_gene",
        ):
            gene = child.get(gene_key, {})
            if isinstance(gene, dict):
                child[gene_key], _ = self._mutate_dict(gene, rng)
        base_id = str(child.get("genome_id", "genome"))
        child["genome_id"] = f"{base_id}_m{rng.randint(1000, 9999)}"
        child["metadata"]["mutation_origin"] = str(genome.get("genome_id", "unknown"))
        child["metadata"]["mutated_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        # --- ResearchMemoryLayer hook ---
        if self._bridge:
            self._bridge.record_mutation(
                parent = genome,
                child  = child,
                ops    = ["gene_mutation"],
            )

        return child

    def _mutate_dict(self, data: Dict, rng: random.Random) -> Tuple[Dict, int]:
        out = {}
        changed = 0
        for key, value in data.items():
            if isinstance(value, dict):
                out[key], c = self._mutate_dict(value, rng)
                changed += c
                continue
            if isinstance(value, list):
                mutated = list(value)
                if mutated and rng.random() < self.mutation_rate:
                    idx = rng.randrange(len(mutated))
                    mutated[idx] = self._mutate_scalar(mutated[idx], rng)
                    changed += 1
                out[key] = mutated
                continue
            if rng.random() < self.mutation_rate:
                out[key] = self._mutate_scalar(value, rng)
                changed += 1
            else:
                out[key] = value
        return out, changed

    def _mutate_scalar(self, value, rng: random.Random):
        if isinstance(value, bool):
            return not value if rng.random() < 0.5 else value
        if isinstance(value, int):
            delta = max(1, int(abs(value) * self.numeric_jitter_pct))
            return max(1, value + rng.randint(-delta, delta))
        if isinstance(value, float):
            delta = abs(value) * self.numeric_jitter_pct
            return round(value + rng.uniform(-delta, delta), 8)
        if isinstance(value, str):
            switches = {
                "EMA": "VWAP",
                "VWAP": "EMA",
                "RSI": "STOCH",
                "STOCH": "RSI",
                "MACD": "AROON",
                "AROON": "MACD",
                "BOLLINGER": "KELTNER",
                "KELTNER": "BOLLINGER",
                "5m": "15m",
                "15m": "1h",
                "1h": "1d",
                "1d": "5m",
            }
            return switches.get(value, value)
        return value


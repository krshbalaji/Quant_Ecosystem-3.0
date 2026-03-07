"""Genome crossbreeder for Alpha Genome Engine."""

from __future__ import annotations

import copy
import random
from datetime import datetime
from typing import Dict, Optional


class GenomeCrossbreeder:
    """Combines genes from two parent genomes into one child.

    ResearchMemoryLayer integration
    --------------------------------
    Pass research_memory=router.research_memory to record every two-parent
    crossover in AlphaMemoryStore and StrategyGenealogy.
    The hook fires after the child is fully stamped — core algorithm unchanged.
    AlphaCrossoverEngine inherits this automatically because it calls
    self._base_crossbreeder.crossbreed(a, b) internally.
    """

    GENE_KEYS = (
        "market_filter_gene",
        "signal_gene",
        "entry_gene",
        "exit_gene",
        "risk_gene",
        "execution_gene",
    )

    def __init__(self, research_memory=None, **kwargs):
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

    def crossbreed(self, parent_a: Dict, parent_b: Dict, seed: int | None = None, regime: str = "all") -> Dict:
        rng = random.Random(seed)
        a = dict(parent_a or {})
        b = dict(parent_b or {})
        child: Dict = {"metadata": {}}
        for key in self.GENE_KEYS:
            source = a if rng.random() < 0.5 else b
            other  = b if source is a else a
            gene   = copy.deepcopy(source.get(key, {}))
            if not gene and other.get(key):
                gene = copy.deepcopy(other.get(key, {}))
            child[key] = gene

        aid = str(a.get("genome_id", "A"))
        bid = str(b.get("genome_id", "B"))
        child["genome_id"] = f"{aid}x{bid}_{rng.randint(1000, 9999)}"
        child["metadata"]["crossbred_from"] = [aid, bid]
        child["metadata"]["crossbred_at"]   = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        # --- ResearchMemoryLayer hook ---
        if self._bridge:
            self._bridge.record_crossover(
                parent_a = parent_a,
                parent_b = parent_b,
                child    = child,
                regime   = regime,
            )

        return child


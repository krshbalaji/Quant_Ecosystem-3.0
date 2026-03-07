"""Genome generator for random, mutation, and crossbreed pipelines."""

from __future__ import annotations

import random
from datetime import datetime
from typing import Dict, Iterable, List, Optional

from quant_ecosystem.alpha_genome.genome_crossbreeder import GenomeCrossbreeder
from quant_ecosystem.alpha_genome.genome_mutator import GenomeMutator


class GenomeGenerator:
    """Generates candidate genomes from multiple sources.

    ResearchMemoryLayer integration
    --------------------------------
    Pass research_memory=router.research_memory to record every generated
    genome in the persistent alpha memory and genealogy systems.
    Pass genome_library=lib to auto-store GenomeRecords on generation.
    Both are optional; omitting them has no effect on the algorithm.
    """

    def __init__(
        self,
        mutator:         GenomeMutator | None = None,
        crossbreeder:    GenomeCrossbreeder | None = None,
        research_memory  = None,
        genome_library   = None,
        **kwargs,
    ):
        self.mutator      = mutator      or GenomeMutator()
        self.crossbreeder = crossbreeder or GenomeCrossbreeder()
        self._library     = genome_library

        # Wire memory bridge
        self._bridge = None
        if research_memory is not None:
            try:
                from quant_ecosystem.alpha_genome._memory_bridge import GenomeMemoryBridge
                self._bridge = GenomeMemoryBridge(research_memory=research_memory)
            except Exception:
                pass

    def set_research_memory(self, research_memory, genome_library=None) -> None:
        """Late injection of ResearchMemoryLayer (called post-boot)."""
        try:
            from quant_ecosystem.alpha_genome._memory_bridge import GenomeMemoryBridge
            self._bridge = GenomeMemoryBridge(research_memory=research_memory)
        except Exception:
            pass
        if genome_library is not None:
            self._library = genome_library

    def generate_random(self, count: int = 10, seed: int | None = None, regime: str = "all") -> List[Dict]:
        rng = random.Random(seed)
        out = []
        for _ in range(max(1, int(count))):
            genome = self._random_genome(rng)
            out.append(genome)
            # Persist seed genome
            if self._bridge:
                self._bridge.record_seed(genome, regime=regime)
            if self._library:
                from quant_ecosystem.alpha_genome.genome_library import GenomeRecord
                self._library.store_record(GenomeRecord.from_genome_dict(genome))
        return out

    def generate_from_mutation(self, base_genomes: Iterable[Dict], variants_per_base: int = 3, regime: str = "all") -> List[Dict]:
        out: List[Dict] = []
        for genome in list(base_genomes or []):
            for _ in range(max(1, int(variants_per_base))):
                child = self.mutator.mutate(genome)
                out.append(child)
                # Genealogy + alpha store recorded inside GenomeMutator hook;
                # also store in library
                if self._library:
                    from quant_ecosystem.alpha_genome.genome_library import GenomeRecord
                    self._library.store_record(GenomeRecord.from_genome_dict(child))
        return out

    def generate_from_crossbreeding(self, parent_genomes: Iterable[Dict], children_count: int = 10, regime: str = "all") -> List[Dict]:
        parents = [dict(item) for item in list(parent_genomes or []) if item]
        if len(parents) < 2:
            return []
        out = []
        rng = random.Random()
        for _ in range(max(1, int(children_count))):
            a, b = rng.sample(parents, 2)
            child = self.crossbreeder.crossbreed(a, b)
            out.append(child)
            # Genealogy + alpha store recorded inside GenomeCrossbreeder hook;
            # also store in library
            if self._library:
                from quant_ecosystem.alpha_genome.genome_library import GenomeRecord
                self._library.store_record(GenomeRecord.from_genome_dict(child))
        return out

    def _random_genome(self, rng: random.Random) -> Dict:
        now = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        signal_type = rng.choice(["momentum", "mean_reversion", "breakout", "volatility", "stat_arb"])
        tf = rng.choice(["5m", "15m", "1h", "1d"])
        return {
            "genome_id": f"gen_{signal_type}_{now}_{rng.randint(100,999)}",
            "market_filter_gene": {
                "volatility_min": round(rng.uniform(0.08, 0.35), 4),
                "session": rng.choice(["ALL", "REGULAR", "HIGH_LIQ"]),
                "asset_class": rng.choice(["stocks", "indices", "forex", "crypto", "commodities"]),
            },
            "signal_gene": {
                "type": signal_type,
                "indicator_1": rng.choice(["EMA", "RSI", "VWAP", "MACD", "BOLLINGER", "KELTNER"]),
                "indicator_2": rng.choice(["ATR", "VOLUME_Z", "AROON", "STOCH"]),
                "threshold": round(rng.uniform(0.45, 0.9), 4),
                "timeframe": tf,
            },
            "entry_gene": {
                "trigger": rng.choice(["cross", "breakout", "pullback"]),
                "confirmation_bars": rng.randint(1, 4),
            },
            "exit_gene": {
                "mode": rng.choice(["tp_sl", "trailing", "signal_flip"]),
                "take_profit_r": round(rng.uniform(1.2, 3.5), 4),
                "stop_loss_r": round(rng.uniform(0.4, 1.5), 4),
            },
            "risk_gene": {
                "risk_pct": round(rng.uniform(0.25, 2.0), 4),
                "max_positions": rng.randint(1, 6),
                "cooldown_cycles": rng.randint(0, 5),
            },
            "execution_gene": {
                "order_type": rng.choice(["market", "limit", "twap", "vwap"]),
                "slippage_bps_limit": round(rng.uniform(2.0, 25.0), 4),
            },
            "metadata": {"source": "random_generator", "created_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")},
        }


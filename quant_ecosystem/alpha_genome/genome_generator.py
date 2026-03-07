"""Genome generator for random, mutation, and crossbreed pipelines."""

from __future__ import annotations

import random
from datetime import datetime
from typing import Dict, Iterable, List

from quant_ecosystem.alpha_genome.genome_crossbreeder import GenomeCrossbreeder
from quant_ecosystem.alpha_genome.genome_mutator import GenomeMutator


class GenomeGenerator:
    """Generates candidate genomes from multiple sources."""

    def __init__(
        self,
        mutator: GenomeMutator | None = None,
        crossbreeder: GenomeCrossbreeder | None = None, **kwargs
    ):
        self.mutator = mutator or GenomeMutator()
        self.crossbreeder = crossbreeder or GenomeCrossbreeder()

    def generate_random(self, count: int = 10, seed: int | None = None) -> List[Dict]:
        rng = random.Random(seed)
        out = []
        for _ in range(max(1, int(count))):
            out.append(self._random_genome(rng))
        return out

    def generate_from_mutation(self, base_genomes: Iterable[Dict], variants_per_base: int = 3) -> List[Dict]:
        out: List[Dict] = []
        for genome in list(base_genomes or []):
            for _ in range(max(1, int(variants_per_base))):
                out.append(self.mutator.mutate(genome))
        return out

    def generate_from_crossbreeding(self, parent_genomes: Iterable[Dict], children_count: int = 10) -> List[Dict]:
        parents = [dict(item) for item in list(parent_genomes or []) if item]
        if len(parents) < 2:
            return []
        out = []
        rng = random.Random()
        for _ in range(max(1, int(children_count))):
            a, b = rng.sample(parents, 2)
            child = self.crossbreeder.crossbreed(a, b)
            out.append(child)
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


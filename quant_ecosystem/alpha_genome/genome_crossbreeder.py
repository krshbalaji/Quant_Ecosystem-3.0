"""Genome crossbreeder for Alpha Genome Engine."""

from __future__ import annotations

import copy
import random
from datetime import datetime
from typing import Dict


class GenomeCrossbreeder:
    """Combines genes from two parent genomes into one child."""

    GENE_KEYS = (
        "market_filter_gene",
        "signal_gene",
        "entry_gene",
        "exit_gene",
        "risk_gene",
        "execution_gene",
    )

    def crossbreed(self, parent_a: Dict, parent_b: Dict, seed: int | None = None) -> Dict:
        rng = random.Random(seed)
        a = dict(parent_a or {})
        b = dict(parent_b or {})
        child: Dict = {"metadata": {}}
        for key in self.GENE_KEYS:
            source = a if rng.random() < 0.5 else b
            other = b if source is a else a
            gene = copy.deepcopy(source.get(key, {}))
            if not gene and other.get(key):
                gene = copy.deepcopy(other.get(key, {}))
            child[key] = gene

        aid = str(a.get("genome_id", "A"))
        bid = str(b.get("genome_id", "B"))
        child["genome_id"] = f"{aid}x{bid}_{rng.randint(1000, 9999)}"
        child["metadata"]["crossbred_from"] = [aid, bid]
        child["metadata"]["crossbred_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        return child


"""
alpha_dna_builder.py
Assembles complete strategy DNA from gene pool selections.
DNA = ordered combination of 6 gene types forming a deployable strategy specification.

Sequence:
  market_filter_gene → signal_gene → entry_gene → exit_gene → risk_gene → execution_gene

The builder supports three construction modes:
  1. random      – sample genes independently from gene pool
  2. family      – sample genes aligned to a single strategy family
  3. directed    – caller specifies gene overrides for targeted construction
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from quant_ecosystem.alpha_genome.alpha_gene_pool import AlphaGene, AlphaGenePool


# ---------------------------------------------------------------------------
# Gene → DNA slot mappings
# ---------------------------------------------------------------------------

# Gene families suitable for each slot — ensures logical coherence
_SLOT_FAMILY_MAP: Dict[str, List[str]] = {
    "market_filter_gene": ["trend", "volatility", "statistical", "volume"],
    "signal_gene":        ["trend", "momentum", "reversion", "volume", "statistical"],
    "entry_gene":         ["momentum", "trend", "volatility"],
    "exit_gene":          ["volatility", "momentum", "reversion"],
    "risk_gene":          ["volatility", "statistical"],
    "execution_gene":     ["volume", "volatility"],
}

# Strategy family presets — bias certain slots toward certain gene families
STRATEGY_FAMILY_PRESETS: Dict[str, Dict[str, str]] = {
    "trend_following": {
        "market_filter_gene": "trend",
        "signal_gene":        "trend",
        "entry_gene":         "trend",
        "exit_gene":          "volatility",
        "risk_gene":          "volatility",
        "execution_gene":     "volume",
    },
    "mean_reversion": {
        "market_filter_gene": "statistical",
        "signal_gene":        "reversion",
        "entry_gene":         "reversion",
        "exit_gene":          "momentum",
        "risk_gene":          "statistical",
        "execution_gene":     "volume",
    },
    "momentum": {
        "market_filter_gene": "volume",
        "signal_gene":        "momentum",
        "entry_gene":         "momentum",
        "exit_gene":          "momentum",
        "risk_gene":          "volatility",
        "execution_gene":     "volume",
    },
    "volatility_breakout": {
        "market_filter_gene": "volatility",
        "signal_gene":        "volatility",
        "entry_gene":         "volatility",
        "exit_gene":          "volatility",
        "risk_gene":          "volatility",
        "execution_gene":     "volume",
    },
    "stat_arb": {
        "market_filter_gene": "statistical",
        "signal_gene":        "statistical",
        "entry_gene":         "reversion",
        "exit_gene":          "reversion",
        "risk_gene":          "statistical",
        "execution_gene":     "volume",
    },
}

_DNA_SLOTS = list(_SLOT_FAMILY_MAP.keys())


class AlphaDNA:
    """Complete strategy DNA — 6 gene slots forming a deployable alpha."""

    def __init__(
        self,
        dna_id: str,
        genes: Dict[str, AlphaGene],
        strategy_family: str = "mixed",
        fitness: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.dna_id = dna_id
        self.genes = genes               # slot_name → AlphaGene
        self.strategy_family = strategy_family
        self.fitness = fitness
        self.metadata = metadata or {}

    def to_genome_dict(self) -> Dict[str, Any]:
        """Convert to the genome dict format used by GenomeEvaluator and StrategyLab."""
        signal_gene = self.genes.get("signal_gene")
        entry_gene = self.genes.get("entry_gene")
        exit_gene = self.genes.get("exit_gene")
        risk_gene = self.genes.get("risk_gene")
        exec_gene = self.genes.get("execution_gene")
        market_filter = self.genes.get("market_filter_gene")

        def p(gene: Optional[AlphaGene]) -> Dict[str, Any]:
            return gene.params if gene else {}

        return {
            "genome_id": self.dna_id,
            "market_filter_gene": {
                "gene_type": market_filter.gene_type if market_filter else "hv_regime",
                **p(market_filter),
            },
            "signal_gene": {
                "type": self.strategy_family,
                "gene_type": signal_gene.gene_type if signal_gene else "ema_cross",
                "indicator_1": (signal_gene.indicators[0].upper() if signal_gene and signal_gene.indicators else "EMA"),
                "indicator_2": (signal_gene.indicators[1].upper() if signal_gene and len(signal_gene.indicators) > 1 else "ATR"),
                "threshold": p(signal_gene).get("threshold", 0.6),
                "timeframe": "5m",
                **p(signal_gene),
            },
            "entry_gene": {
                "trigger": "cross",
                "confirmation_bars": int(p(entry_gene).get("confirmation_bars", 2)),
                **p(entry_gene),
            },
            "exit_gene": {
                "mode": "tp_sl",
                "take_profit_r": float(p(exit_gene).get("take_profit_r", 2.0)),
                "stop_loss_r": float(p(exit_gene).get("stop_loss_r", 1.0)),
                **p(exit_gene),
            },
            "risk_gene": {
                "risk_pct": float(p(risk_gene).get("risk_pct", 1.0)),
                "max_positions": int(p(risk_gene).get("max_positions", 3)),
                "cooldown_cycles": int(p(risk_gene).get("cooldown_cycles", 1)),
                **p(risk_gene),
            },
            "execution_gene": {
                "order_type": "market",
                "slippage_bps_limit": float(p(exec_gene).get("slippage_bps_limit", 10.0)),
                **p(exec_gene),
            },
            "metadata": {
                "dna_id": self.dna_id,
                "strategy_family": self.strategy_family,
                "fitness": self.fitness,
                "built_at": self.metadata.get("built_at", datetime.utcnow().isoformat() + "Z"),
                **self.metadata,
            },
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dna_id": self.dna_id,
            "strategy_family": self.strategy_family,
            "fitness": self.fitness,
            "genes": {slot: gene.to_dict() for slot, gene in self.genes.items()},
            "metadata": self.metadata,
        }


class AlphaDNABuilder:
    """
    Builds AlphaDNA from a gene pool.

    Usage:
        builder = AlphaDNABuilder(gene_pool)
        dna = builder.build_random()
        dna = builder.build_family("trend_following")
        dna = builder.build_directed(signal_gene=my_gene, risk_gene=my_risk_gene)
        genome = dna.to_genome_dict()   # → compatible with GenomeEvaluator
    """

    def __init__(self, gene_pool: AlphaGenePool) -> None:
        self.pool = gene_pool

    # ------------------------------------------------------------------
    # Build modes
    # ------------------------------------------------------------------

    def build_random(self) -> AlphaDNA:
        """Construct DNA by sampling random genes for each slot."""
        genes = {}
        for slot in _DNA_SLOTS:
            families = _SLOT_FAMILY_MAP[slot]
            gene = self._sample_any_family(families)
            if gene is None:
                gene = self._fallback_gene(slot)
            genes[slot] = gene
        return self._assemble("mixed", genes)

    def build_family(self, family: str) -> AlphaDNA:
        """Construct DNA biased toward a named strategy family preset."""
        preset = STRATEGY_FAMILY_PRESETS.get(family, STRATEGY_FAMILY_PRESETS["trend_following"])
        genes = {}
        for slot in _DNA_SLOTS:
            preferred_family = preset.get(slot, _SLOT_FAMILY_MAP[slot][0])
            gene = self._sample_family(preferred_family)
            if gene is None:
                # Fallback to any valid family for this slot
                gene = self._sample_any_family(_SLOT_FAMILY_MAP[slot])
            if gene is None:
                gene = self._fallback_gene(slot)
            genes[slot] = gene
        return self._assemble(family, genes)

    def build_directed(
        self,
        strategy_family: str = "mixed",
        market_filter_gene: Optional[AlphaGene] = None,
        signal_gene: Optional[AlphaGene] = None,
        entry_gene: Optional[AlphaGene] = None,
        exit_gene: Optional[AlphaGene] = None,
        risk_gene: Optional[AlphaGene] = None,
        execution_gene: Optional[AlphaGene] = None,
    ) -> AlphaDNA:
        """Build DNA with caller-specified gene overrides; missing slots sampled randomly."""
        overrides = {
            "market_filter_gene": market_filter_gene,
            "signal_gene": signal_gene,
            "entry_gene": entry_gene,
            "exit_gene": exit_gene,
            "risk_gene": risk_gene,
            "execution_gene": execution_gene,
        }
        genes = {}
        for slot in _DNA_SLOTS:
            gene = overrides.get(slot)
            if gene is None:
                gene = self._sample_any_family(_SLOT_FAMILY_MAP[slot])
            if gene is None:
                gene = self._fallback_gene(slot)
            genes[slot] = gene
        return self._assemble(strategy_family, genes)

    def build_batch(self, count: int, family: Optional[str] = None) -> List[AlphaDNA]:
        """Build multiple DNA strands, optionally all from the same family."""
        families = list(STRATEGY_FAMILY_PRESETS.keys())
        out = []
        for i in range(count):
            f = family or families[i % len(families)]
            out.append(self.build_family(f))
        return out

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sample_family(self, family: str) -> Optional[AlphaGene]:
        pool = self.pool.by_family(family)
        if not pool:
            return None
        return random.choice(pool)

    def _sample_any_family(self, families: List[str]) -> Optional[AlphaGene]:
        random.shuffle(families)
        for f in families:
            g = self._sample_family(f)
            if g is not None:
                return g
        return None

    def _fallback_gene(self, slot: str) -> AlphaGene:
        """Generate a fresh random gene when the pool is empty for a slot."""
        from quant_ecosystem.alpha_genome.alpha_gene_pool import GENE_TEMPLATES
        slot_families = _SLOT_FAMILY_MAP[slot]
        candidates = [
            gt for gt, tpl in GENE_TEMPLATES.items()
            if tpl["family"] in slot_families
        ]
        gene_type = random.choice(candidates) if candidates else list(GENE_TEMPLATES.keys())[0]
        return AlphaGene.random(gene_type)

    def _assemble(self, family: str, genes: Dict[str, AlphaGene]) -> AlphaDNA:
        dna_id = f"dna_{family}_{uuid.uuid4().hex[:10]}"
        metadata = {
            "built_at": datetime.utcnow().isoformat() + "Z",
            "strategy_family": family,
            "gene_ids": {slot: g.gene_id for slot, g in genes.items()},
        }
        return AlphaDNA(dna_id, genes, strategy_family=family, metadata=metadata)

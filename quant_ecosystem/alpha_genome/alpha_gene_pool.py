"""
alpha_gene_pool.py
Gene pool management for the alpha genome research pipeline.
Each 'gene' is a parameterised alpha expression — an atomic trading logic unit.
Genes combine into DNA (full strategies) via the DNA builder.
"""

from __future__ import annotations

import json
import random
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

_POOL_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "gene_pool"
_POOL_PATH.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Gene Definition
# ---------------------------------------------------------------------------

# Each gene type specifies:
#   - which indicators it uses
#   - parameter ranges
#   - signal interpretation

GENE_TEMPLATES: Dict[str, Dict[str, Any]] = {
    # --- Trend genes ---
    "ema_cross": {
        "family": "trend",
        "indicators": ["ema"],
        "params": {
            "fast_period": (5, 15),
            "slow_period": (20, 60),
        },
        "signal_logic": "ema_fast > ema_slow → BUY, ema_fast < ema_slow → SELL",
    },
    "macd_zero_cross": {
        "family": "trend",
        "indicators": ["macd"],
        "params": {
            "fast": (8, 16),
            "slow": (20, 32),
            "signal": (5, 12),
        },
        "signal_logic": "macd_line crosses above 0 → BUY",
    },
    "hma_direction": {
        "family": "trend",
        "indicators": ["hma"],
        "params": {"period": (10, 30)},
        "signal_logic": "HMA rising → BUY, falling → SELL",
    },
    # --- Momentum genes ---
    "rsi_threshold": {
        "family": "momentum",
        "indicators": ["rsi"],
        "params": {
            "period": (7, 21),
            "oversold": (20, 40),
            "overbought": (60, 80),
        },
        "signal_logic": "rsi < oversold → BUY, rsi > overbought → SELL",
    },
    "stoch_cross": {
        "family": "momentum",
        "indicators": ["stochastic"],
        "params": {
            "k_period": (9, 21),
            "d_period": (3, 7),
            "threshold": (20, 35),
        },
        "signal_logic": "K crosses D in oversold zone → BUY",
    },
    "roc_breakout": {
        "family": "momentum",
        "indicators": ["roc"],
        "params": {"period": (5, 20), "threshold_pct": (0.5, 3.0)},
        "signal_logic": "ROC > threshold → momentum signal",
    },
    # --- Volatility genes ---
    "bollinger_squeeze": {
        "family": "volatility",
        "indicators": ["bollinger", "keltner"],
        "params": {
            "bb_period": (15, 25),
            "kc_period": (15, 25),
            "bb_std": (1.5, 2.5),
        },
        "signal_logic": "BB inside KC (squeeze) → prepare for breakout",
    },
    "atr_breakout": {
        "family": "volatility",
        "indicators": ["atr", "ema"],
        "params": {
            "atr_period": (10, 21),
            "ema_period": (15, 50),
            "atr_multiplier": (1.0, 3.0),
        },
        "signal_logic": "price breaks ema ± ATR*mult → trend signal",
    },
    "hv_regime": {
        "family": "volatility",
        "indicators": ["hv"],
        "params": {
            "short_period": (10, 21),
            "long_period": (42, 90),
        },
        "signal_logic": "hv_short > hv_long * 1.3 → high vol regime",
    },
    # --- Mean Reversion genes ---
    "zscore_reversion": {
        "family": "reversion",
        "indicators": ["zscore"],
        "params": {
            "period": (15, 40),
            "entry_zscore": (1.5, 3.0),
            "exit_zscore": (0.0, 0.5),
        },
        "signal_logic": "zscore < -entry → BUY, zscore > entry → SELL",
    },
    "bb_reversion": {
        "family": "reversion",
        "indicators": ["bollinger"],
        "params": {
            "period": (15, 25),
            "std_dev": (1.5, 2.5),
        },
        "signal_logic": "price < lower band → BUY, > upper → SELL",
    },
    "rsi_mean_reversion": {
        "family": "reversion",
        "indicators": ["rsi"],
        "params": {
            "period": (5, 14),
            "short_threshold": (15, 30),
        },
        "signal_logic": "rsi < threshold in trending market → counter-trend",
    },
    # --- Volume genes ---
    "volume_spike": {
        "family": "volume",
        "indicators": ["volume_zscore"],
        "params": {
            "period": (15, 30),
            "spike_threshold": (1.5, 3.0),
        },
        "signal_logic": "volume_z > threshold → attention signal",
    },
    "cmf_momentum": {
        "family": "volume",
        "indicators": ["cmf"],
        "params": {"period": (14, 28), "threshold": (0.05, 0.2)},
        "signal_logic": "CMF > threshold → buy pressure confirmed",
    },
    # --- Statistical genes ---
    "hurst_regime": {
        "family": "statistical",
        "indicators": ["hurst"],
        "params": {"window": (30, 60)},
        "signal_logic": "H > 0.6 → trend, H < 0.4 → reversion",
    },
    "autocorr_reversion": {
        "family": "statistical",
        "indicators": ["autocorrelation"],
        "params": {"lag": (1, 3), "period": (20, 60)},
        "signal_logic": "strong negative autocorr → reversion setup",
    },
}


class AlphaGene:
    """A single alpha gene — atomic trading logic with parameters."""

    def __init__(self, gene_type: str, params: Dict[str, float],
                 gene_id: Optional[str] = None, fitness: float = 0.0) -> None:
        if gene_type not in GENE_TEMPLATES:
            raise ValueError(f"Unknown gene type: {gene_type}")
        self.gene_id = gene_id or str(uuid.uuid4())[:12]
        self.gene_type = gene_type
        self.params = params
        self.fitness = fitness
        self.template = GENE_TEMPLATES[gene_type]

    @property
    def family(self) -> str:
        return self.template["family"]

    @property
    def indicators(self) -> List[str]:
        return self.template["indicators"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gene_id": self.gene_id,
            "gene_type": self.gene_type,
            "family": self.family,
            "indicators": self.indicators,
            "params": self.params,
            "fitness": self.fitness,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> AlphaGene:
        g = cls(d["gene_type"], d["params"], d.get("gene_id"), d.get("fitness", 0.0))
        return g

    @classmethod
    def random(cls, gene_type: str) -> AlphaGene:
        """Generate a gene with randomly sampled parameters."""
        template = GENE_TEMPLATES[gene_type]
        params = {}
        for name, bounds in template["params"].items():
            lo, hi = bounds
            if isinstance(lo, int) and isinstance(hi, int):
                params[name] = float(random.randint(lo, hi))
            else:
                params[name] = round(random.uniform(lo, hi), 4)
        return cls(gene_type, params)


class AlphaGenePool:
    """
    Thread-safe registry of all known alpha genes.
    Provides sampling, ranking, and persistence.
    """

    def __init__(self, pool_path: Optional[Path] = None) -> None:
        self._path = pool_path or _POOL_PATH / "gene_pool.json"
        self._genes: Dict[str, AlphaGene] = {}
        self._lock = threading.Lock()
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            with open(self._path) as f:
                data = json.load(f)
            for d in data.get("genes", []):
                g = AlphaGene.from_dict(d)
                self._genes[g.gene_id] = g
        except Exception:
            pass

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w") as f:
            json.dump(
                {"genes": [g.to_dict() for g in self._genes.values()]}, f, indent=2
            )

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add(self, gene: AlphaGene) -> None:
        with self._lock:
            self._genes[gene.gene_id] = gene
            self._save()

    def add_many(self, genes: List[AlphaGene]) -> None:
        with self._lock:
            for g in genes:
                self._genes[g.gene_id] = g
            self._save()

    def update_fitness(self, gene_id: str, fitness: float) -> None:
        with self._lock:
            if gene_id in self._genes:
                self._genes[gene_id].fitness = fitness
                self._save()

    def remove(self, gene_id: str) -> None:
        with self._lock:
            self._genes.pop(gene_id, None)
            self._save()

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get(self, gene_id: str) -> Optional[AlphaGene]:
        return self._genes.get(gene_id)

    def all(self) -> List[AlphaGene]:
        return list(self._genes.values())

    def by_family(self, family: str) -> List[AlphaGene]:
        return [g for g in self._genes.values() if g.family == family]

    def top_n(self, n: int = 20) -> List[AlphaGene]:
        return sorted(self._genes.values(), key=lambda g: g.fitness, reverse=True)[:n]

    def sample(self, n: int = 5, family: Optional[str] = None) -> List[AlphaGene]:
        """Sample n genes, optionally filtered by family."""
        pool = self.by_family(family) if family else self.all()
        if not pool:
            return []
        k = min(n, len(pool))
        return random.sample(pool, k)

    def sample_random_types(self, n: int = 6) -> List[AlphaGene]:
        """Sample n genes of different types for diversity."""
        types = list(GENE_TEMPLATES.keys())
        random.shuffle(types)
        genes = []
        for t in types[:n]:
            genes.append(AlphaGene.random(t))
        return genes

    def seed_from_templates(self, count_per_type: int = 3) -> None:
        """Populate pool with random genes from all templates."""
        genes = []
        for gene_type in GENE_TEMPLATES:
            for _ in range(count_per_type):
                genes.append(AlphaGene.random(gene_type))
        self.add_many(genes)

    def prune(self, min_fitness: float = -0.5, keep_top: int = 200) -> int:
        """Remove low-fitness genes, keep pool healthy."""
        with self._lock:
            sorted_genes = sorted(
                self._genes.values(), key=lambda g: g.fitness, reverse=True
            )
            keep = sorted_genes[:keep_top]
            keep = [g for g in keep if g.fitness >= min_fitness]
            self._genes = {g.gene_id: g for g in keep}
            self._save()
            return len(keep)

    def __len__(self) -> int:
        return len(self._genes)

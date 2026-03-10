"""
quant_ecosystem/mutation/strategy_mutation_extension.py
========================================================
Strategy Parameter Mutation Extension — Quant Ecosystem 3.0

Extends the core StrategyMutationEngine with advanced mutation operators:

    ┌──────────────────────────────────────────────────────────────────┐
    │              StrategyMutationExtension                          │
    │  (wraps / augments existing StrategyMutationEngine)             │
    └──────────────┬──────────────────────────────────────────────────┘
                   │  delegates mutation + adds:
    ┌──────────────▼──────────────────────────────────────────────────┐
    │  AdaptiveMutationScheduler                                      │
    │  — fitness-gradient controlled mutation rate                    │
    │  — regime-aware parameter range bias                            │
    │  — parameter heat-map (which params improve fitness most)       │
    └─────────────────────────────────────────────────────────────────┘
    ┌─────────────────────────────────────────────────────────────────┐
    │  MutationOperators                                              │
    │  — gaussian_perturbation   small random walk                   │
    │  — directional_step        step in direction of fitness gain    │
    │  — regime_bias             clamp param range to regime profile  │
    │  — crossbreed_params       splice params from two parents       │
    │  — random_restart          sample fresh from full param space   │
    │  — simulated_annealing     accept worse params with decay prob  │
    └─────────────────────────────────────────────────────────────────┘

Design principles
-----------------
- Non-invasive: wraps existing StrategyMutationEngine via composition,
  never monkey-patches or modifies its internals.
- All mutation methods return a new param dict, never mutate in-place.
- Thread-safe: internal state guarded by threading.Lock.
- Regime-aware: adapts mutation range bounds to current market regime.
- Tracks per-parameter fitness improvement history for heat-map scoring.

Usage
-----
    ext = StrategyMutationExtension(
        base_mutation_engine = router.mutation_engine,
        regime_engine        = router.regime_intelligence,
    )

    # Augmented mutation — picks best operator based on history
    new_params = ext.mutate(genome)

    # Crossbreed two parent genomes
    child = ext.crossbreed(parent_a, parent_b)

    # Stats / diagnostics
    ext.stats()
"""

from __future__ import annotations

import copy
import logging
import math
import random
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_TAG = "[mutation_ext]"


# ─────────────────────────────────────────────────────────────────────────────
# Regime → parameter bias profiles
# ─────────────────────────────────────────────────────────────────────────────

# For each known regime, hints for common parameter names:
#   (scale_factor, direction)  — multiply default range by scale, bias direction
_REGIME_PARAM_BIAS: Dict[str, Dict[str, Tuple[float, float]]] = {
    "TRENDING": {
        "period":          (1.3,  0.0),   # prefer longer periods
        "lookback":        (1.3,  0.0),
        "fast_period":     (0.8, -1.0),   # smaller fast window
        "slow_period":     (1.3,  1.0),   # larger slow window
        "stop_loss":       (1.2,  0.0),   # wider stop
        "take_profit":     (1.5,  0.0),   # bigger take-profit
    },
    "RANGE_BOUND": {
        "period":          (0.7,  0.0),   # shorter reversion periods
        "lookback":        (0.7,  0.0),
        "threshold":       (0.8, -1.0),   # tighter threshold
        "stop_loss":       (0.8,  0.0),   # tighter stop
        "take_profit":     (0.7,  0.0),
        "rsi_upper":       (1.0,  1.0),   # nudge overbought threshold up
        "rsi_lower":       (1.0, -1.0),
    },
    "VOLATILE": {
        "atr_multiplier":  (1.5,  1.0),
        "stop_loss":       (1.5,  0.0),
        "position_size":   (0.6, -1.0),   # reduce position size
        "period":          (0.8,  0.0),   # shorter for fast reaction
    },
    "BREAKOUT": {
        "breakout_period": (1.2,  1.0),
        "volume_threshold":(1.3,  1.0),
        "stop_loss":       (1.3,  0.0),
        "take_profit":     (1.8,  1.0),
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Parameter schema helpers
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ParamSchema:
    """Describes the valid range and type for one strategy parameter."""
    name:     str
    lo:       float
    hi:       float
    dtype:    str  = "float"  # "float" | "int" | "bool" | "choice"
    choices:  List[Any] = field(default_factory=list)
    step:     float = 0.0    # 0 = continuous

    def clamp(self, v: float) -> float:
        return max(self.lo, min(self.hi, v))

    def cast(self, v: float) -> Any:
        if self.dtype == "int":
            return int(round(v))
        if self.dtype == "bool":
            return bool(round(v))
        if self.dtype == "choice" and self.choices:
            idx = int(round(v)) % len(self.choices)
            return self.choices[idx]
        if self.step > 0:
            return round(round(v / self.step) * self.step, 8)
        return float(v)


# ─────────────────────────────────────────────────────────────────────────────
# Operator implementations
# ─────────────────────────────────────────────────────────────────────────────

class MutationOperators:
    """
    Stateless mutation operators.  All methods return a new params dict.
    """

    @staticmethod
    def gaussian_perturbation(
        params: Dict[str, Any],
        schemas: Dict[str, ParamSchema],
        sigma_scale: float = 0.05,
    ) -> Dict[str, Any]:
        """Small Gaussian random walk in parameter space."""
        out = dict(params)
        for name, val in params.items():
            schema = schemas.get(name)
            if schema is None:
                continue
            rang = schema.hi - schema.lo
            delta = random.gauss(0.0, sigma_scale * rang)
            new_v = schema.clamp(float(val) + delta)
            out[name] = schema.cast(new_v)
        return out

    @staticmethod
    def directional_step(
        params: Dict[str, Any],
        schemas: Dict[str, ParamSchema],
        gradient: Dict[str, float],   # {param_name: fitness_gradient}
        step_scale: float = 0.02,
    ) -> Dict[str, Any]:
        """
        Move each parameter in the direction of its fitness gradient.
        gradient[name] > 0 means increasing the param improved fitness.
        """
        out = dict(params)
        for name, val in params.items():
            schema = schemas.get(name)
            g      = gradient.get(name, 0.0)
            if schema is None or g == 0.0:
                continue
            rang  = schema.hi - schema.lo
            step  = math.copysign(step_scale * rang, g)
            new_v = schema.clamp(float(val) + step)
            out[name] = schema.cast(new_v)
        return out

    @staticmethod
    def regime_bias(
        params: Dict[str, Any],
        schemas: Dict[str, ParamSchema],
        regime: str,
        bias_strength: float = 0.3,
    ) -> Dict[str, Any]:
        """
        Nudge parameters toward the regime-preferred range.
        bias_strength 0 = no nudge, 1 = jump straight to bias target.
        """
        bias_map = _REGIME_PARAM_BIAS.get(regime.upper(), {})
        out      = dict(params)
        for name, val in params.items():
            schema = schemas.get(name)
            bias   = bias_map.get(name)
            if schema is None or bias is None:
                continue
            _scale, direction = bias
            rang  = schema.hi - schema.lo
            target = float(val) + direction * bias_strength * rang * 0.1
            out[name] = schema.cast(schema.clamp(target))
        return out

    @staticmethod
    def crossbreed(
        parent_a: Dict[str, Any],
        parent_b: Dict[str, Any],
        schemas: Dict[str, ParamSchema],
        blend_alpha: float = 0.5,
    ) -> Dict[str, Any]:
        """
        BLX-alpha crossover: each child param is sampled from an expanded
        interval around [min(a,b), max(a,b)].
        """
        child = {}
        for name in set(parent_a) | set(parent_b):
            schema = schemas.get(name)
            va = float(parent_a.get(name, 0))
            vb = float(parent_b.get(name, 0))
            lo_, hi_ = min(va, vb), max(va, vb)
            expand   = blend_alpha * (hi_ - lo_)
            sampled  = random.uniform(lo_ - expand, hi_ + expand)
            if schema:
                child[name] = schema.cast(schema.clamp(sampled))
            else:
                child[name] = sampled
        return child

    @staticmethod
    def random_restart(
        schemas: Dict[str, ParamSchema],
    ) -> Dict[str, Any]:
        """Sample a completely fresh parameter set from the full schema space."""
        out = {}
        for name, schema in schemas.items():
            if schema.dtype == "choice" and schema.choices:
                out[name] = random.choice(schema.choices)
            else:
                v = random.uniform(schema.lo, schema.hi)
                out[name] = schema.cast(v)
        return out

    @staticmethod
    def simulated_annealing(
        params: Dict[str, Any],
        candidate: Dict[str, Any],
        current_fitness: float,
        candidate_fitness: float,
        temperature: float,
    ) -> Dict[str, Any]:
        """
        Accept a worse candidate with probability exp(ΔE / T).
        Returns candidate if accepted, else params.
        """
        if candidate_fitness >= current_fitness:
            return candidate
        if temperature <= 0:
            return params
        delta = candidate_fitness - current_fitness  # negative
        prob  = math.exp(delta / temperature)
        return candidate if random.random() < prob else params


# ─────────────────────────────────────────────────────────────────────────────
# Adaptive Mutation Scheduler
# ─────────────────────────────────────────────────────────────────────────────

class AdaptiveMutationScheduler:
    """
    Tracks per-parameter fitness improvement history and adapts mutation
    rate and operator selection accordingly.

    Fitness stagnation → increase mutation rate (exploration).
    Consistent improvement → reduce mutation rate (exploitation).
    """

    def __init__(
        self,
        base_rate:    float = 0.15,
        min_rate:     float = 0.02,
        max_rate:     float = 0.60,
        window:       int   = 20,
        adapt_speed:  float = 0.10,
    ) -> None:
        self.base_rate   = base_rate
        self.min_rate    = min_rate
        self.max_rate    = max_rate
        self.window      = window
        self.adapt_speed = adapt_speed

        self._fitness_history: List[float] = []
        self._mutation_rate:   float        = base_rate

        # Per-parameter gradient estimates: {param_name: list[float]}
        self._param_gradients: Dict[str, List[float]] = defaultdict(list)
        self._param_history:   List[Tuple[Dict[str, Any], float]] = []
        self._max_param_history = 200

    @property
    def mutation_rate(self) -> float:
        return self._mutation_rate

    def record_fitness(self, fitness: float) -> None:
        """Update fitness history and adapt mutation rate."""
        self._fitness_history.append(fitness)
        if len(self._fitness_history) > self.window:
            self._fitness_history.pop(0)

        if len(self._fitness_history) < 5:
            return

        # Compute improvement trend
        first_half = self._fitness_history[:len(self._fitness_history)//2]
        second_half= self._fitness_history[len(self._fitness_history)//2:]
        trend = (sum(second_half)/len(second_half)) - (sum(first_half)/len(first_half))

        # Stagnation → explore more; improvement → exploit more
        if trend < 0.001:   # stagnating
            target = min(self.max_rate, self._mutation_rate * (1 + self.adapt_speed))
        else:               # improving
            target = max(self.min_rate, self._mutation_rate * (1 - self.adapt_speed * 0.5))

        self._mutation_rate = target

    def record_param_outcome(
        self,
        before: Dict[str, Any],
        after:  Dict[str, Any],
        fitness_before: float,
        fitness_after:  float,
    ) -> None:
        """Record which parameter changes led to fitness improvement."""
        delta_f = fitness_after - fitness_before
        for name in set(before) & set(after):
            delta_p = float(after[name]) - float(before[name])
            if delta_p != 0:
                grad = delta_f / abs(delta_p)
                self._param_gradients[name].append(grad)
                if len(self._param_gradients[name]) > 50:
                    self._param_gradients[name].pop(0)

    def gradient_for(self, name: str) -> float:
        """Return mean gradient (fitness sensitivity) for a parameter."""
        grads = self._param_gradients.get(name, [])
        if not grads:
            return 0.0
        return sum(grads) / len(grads)

    def all_gradients(self) -> Dict[str, float]:
        return {k: self.gradient_for(k) for k in self._param_gradients}

    def best_operator(self, n_recent: int = 10) -> str:
        """
        Heuristically suggest the best mutation operator based on current
        fitness trend.
        """
        if len(self._fitness_history) < 5:
            return "gaussian"
        trend = self._fitness_history[-1] - self._fitness_history[0]
        if trend > 0.05:
            return "directional"   # exploit gradient
        if trend < -0.05:
            return "random_restart"  # escape
        return "gaussian"            # explore locally

    def temperature(self, max_temp: float = 1.0) -> float:
        """Annealing temperature based on stagnation depth."""
        if len(self._fitness_history) < 2:
            return max_temp
        best   = max(self._fitness_history)
        recent = self._fitness_history[-1]
        stagnation = max(0.0, (best - recent) / (abs(best) + 1e-9))
        return max_temp * stagnation


# ─────────────────────────────────────────────────────────────────────────────
# Main extension class
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class MutationExtensionConfig:
    """Configuration for StrategyMutationExtension."""
    base_mutation_rate:    float = 0.15
    min_mutation_rate:     float = 0.02
    max_mutation_rate:     float = 0.60
    adaptation_window:     int   = 20
    regime_bias_strength:  float = 0.25
    crossbreed_alpha:      float = 0.5
    sa_max_temperature:    float = 0.5
    gaussian_sigma_scale:  float = 0.05
    directional_step_scale:float = 0.02
    enable_regime_bias:    bool  = True
    enable_adaptive_rate:  bool  = True
    enable_sa:             bool  = False   # simulated annealing gate


class StrategyMutationExtension:
    """
    Drop-in extension that wraps an existing StrategyMutationEngine and
    augments it with adaptive, regime-aware, gradient-guided mutation.

    Construction
    ------------
        ext = StrategyMutationExtension(
            base_mutation_engine = router.mutation_engine,
            regime_engine        = router.regime_intelligence,
            cfg                  = MutationExtensionConfig(),
        )

    Key methods
    -----------
        mutate(genome)             → new genome dict
        crossbreed(genome_a, genome_b) → child genome dict
        record_outcome(before, after, f_before, f_after)
        stats()                    → dict
        attach_regime_engine(eng)
    """

    def __init__(
        self,
        base_mutation_engine: Any                          = None,
        regime_engine:        Any                          = None,
        cfg:                  Optional[MutationExtensionConfig] = None,
        **kwargs,
    ) -> None:
        self._base    = base_mutation_engine
        self._regime  = regime_engine
        self._cfg     = cfg or MutationExtensionConfig()
        self._ops     = MutationOperators()
        self._lock    = threading.Lock()

        self._scheduler = AdaptiveMutationScheduler(
            base_rate    = self._cfg.base_mutation_rate,
            min_rate     = self._cfg.min_mutation_rate,
            max_rate     = self._cfg.max_mutation_rate,
            window       = self._cfg.adaptation_window,
        )

        # Counters for stats
        self._total_mutations:  int = 0
        self._total_crossbreeds:int = 0
        self._operator_counts: Dict[str, int] = defaultdict(int)

        logger.info(
            "%s StrategyMutationExtension initialized | base=%s",
            _TAG, type(base_mutation_engine).__name__ if base_mutation_engine else "None",
        )

    # ── Genome utilities ──────────────────────────────────────────────────────

    @staticmethod
    def _extract_params(genome: Any) -> Dict[str, Any]:
        """Extract the param dict from a genome object or dict."""
        if isinstance(genome, dict):
            return genome.get("params", genome)
        return getattr(genome, "params", {})

    @staticmethod
    def _extract_schemas(genome: Any) -> Dict[str, ParamSchema]:
        """
        Build ParamSchema objects from genome metadata.
        Supports:
            genome.param_space  — dict {name: {"lo": x, "hi": y, "dtype": z}}
            genome.params       — fallback: build open-ended schemas from values
        """
        raw_space = None
        if isinstance(genome, dict):
            raw_space = genome.get("param_space")
        else:
            raw_space = getattr(genome, "param_space", None)

        if raw_space:
            schemas = {}
            for name, spec in raw_space.items():
                if isinstance(spec, ParamSchema):
                    schemas[name] = spec
                    continue
                lo    = float(spec.get("lo",   spec.get("min", 0)))
                hi    = float(spec.get("hi",   spec.get("max", 1)))
                dtype = str(spec.get("dtype", "float"))
                step  = float(spec.get("step", 0))
                choices = list(spec.get("choices", []))
                schemas[name] = ParamSchema(name, lo, hi, dtype, choices, step)
            return schemas

        # Fallback: infer from current param values with wide defaults
        params = StrategyMutationExtension._extract_params(genome)
        schemas = {}
        for name, val in params.items():
            try:
                fval = float(val)
                lo   = fval * 0.1 if fval > 0 else fval * 2
                hi   = fval * 3.0 if fval > 0 else fval * 0.1
                lo, hi = min(lo, hi), max(lo, hi)
                if lo == hi:
                    lo, hi = lo - 1, hi + 1
                schemas[name] = ParamSchema(name, lo, hi, "float")
            except (TypeError, ValueError):
                pass
        return schemas

    # ── Core mutation API ─────────────────────────────────────────────────────

    def mutate(
        self,
        genome: Any,
        current_fitness: Optional[float] = None,
        operator:        Optional[str]   = None,
    ) -> Any:
        """
        Produce a mutated copy of *genome* using the best available operator.

        Parameters
        ----------
        genome          : genome object or dict
        current_fitness : optional, used by SA and rate adaptation
        operator        : force a specific operator name (or None = auto-select)

        Returns
        -------
        New genome dict with mutated params.
        """
        params  = self._extract_params(genome)
        schemas = self._extract_schemas(genome)

        if not params:
            logger.warning("%s mutate() called on genome with empty params", _TAG)
            return copy.deepcopy(genome)

        # Auto-select operator
        if operator is None:
            operator = self._scheduler.best_operator()
        if not self._cfg.enable_adaptive_rate:
            operator = "gaussian"

        # Build gradient map
        gradients = self._scheduler.all_gradients()

        # Apply selected operator
        if operator == "directional" and gradients:
            new_params = self._ops.directional_step(
                params, schemas, gradients,
                step_scale=self._cfg.directional_step_scale,
            )
        elif operator == "random_restart":
            new_params = self._ops.random_restart(schemas)
        else:
            sigma = self._cfg.gaussian_sigma_scale * self._scheduler.mutation_rate / self._cfg.base_mutation_rate
            new_params = self._ops.gaussian_perturbation(params, schemas, sigma_scale=sigma)

        # Regime bias overlay
        if self._cfg.enable_regime_bias:
            regime = self._current_regime()
            if regime and regime != "UNKNOWN":
                new_params = self._ops.regime_bias(
                    new_params, schemas, regime,
                    bias_strength=self._cfg.regime_bias_strength,
                )

        # Simulated annealing acceptance
        if self._cfg.enable_sa and current_fitness is not None:
            temp = self._scheduler.temperature(self._cfg.sa_max_temperature)
            if temp > 0:
                new_params = self._ops.simulated_annealing(
                    params, new_params,
                    current_fitness, current_fitness,  # candidate fitness unknown
                    temperature=temp,
                )

        with self._lock:
            self._total_mutations += 1
            self._operator_counts[operator] += 1

        return self._rebuild_genome(genome, new_params)

    def crossbreed(
        self,
        genome_a: Any,
        genome_b: Any,
        blend_alpha: Optional[float] = None,
    ) -> Any:
        """
        Produce a child genome by BLX-alpha crossover of two parents.

        Returns a new genome dict.  The child inherits the genome_a
        structure with crossbred params.
        """
        params_a  = self._extract_params(genome_a)
        params_b  = self._extract_params(genome_b)
        schemas_a = self._extract_schemas(genome_a)

        alpha     = blend_alpha if blend_alpha is not None else self._cfg.crossbreed_alpha
        child_params = self._ops.crossbreed(params_a, params_b, schemas_a, blend_alpha=alpha)

        with self._lock:
            self._total_crossbreeds += 1
            self._operator_counts["crossbreed"] += 1

        return self._rebuild_genome(genome_a, child_params)

    # ── Feedback ──────────────────────────────────────────────────────────────

    def record_outcome(
        self,
        before:         Any,
        after:          Any,
        fitness_before: float,
        fitness_after:  float,
    ) -> None:
        """
        Feed back the fitness delta from a mutation so the scheduler
        can adapt future mutation rates and gradients.

        Call this after evaluating a mutated genome.
        """
        p_before = self._extract_params(before)
        p_after  = self._extract_params(after)

        self._scheduler.record_fitness(fitness_after)
        self._scheduler.record_param_outcome(p_before, p_after, fitness_before, fitness_after)

    # ── Attach / detach engines ───────────────────────────────────────────────

    def attach_regime_engine(self, engine: Any) -> None:
        self._regime = engine
        logger.info("%s Regime engine attached: %s", _TAG, type(engine).__name__)

    def attach_base_engine(self, engine: Any) -> None:
        self._base = engine
        logger.info("%s Base mutation engine attached: %s", _TAG, type(engine).__name__)

    # ── Diagnostics ───────────────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_mutations":    self._total_mutations,
                "total_crossbreeds":  self._total_crossbreeds,
                "current_rate":       round(self._scheduler.mutation_rate, 4),
                "operator_counts":    dict(self._operator_counts),
                "top_param_gradients": {
                    k: round(v, 4)
                    for k, v in sorted(
                        self._scheduler.all_gradients().items(),
                        key=lambda x: abs(x[1]),
                        reverse=True,
                    )[:10]
                },
                "current_regime":     self._current_regime(),
                "temperature":        round(self._scheduler.temperature(self._cfg.sa_max_temperature), 4),
            }

    # ── Internals ─────────────────────────────────────────────────────────────

    def _current_regime(self) -> str:
        if self._regime is None:
            return "UNKNOWN"
        try:
            if hasattr(self._regime, "get_regime"):
                return str(self._regime.get_regime())
            if hasattr(self._regime, "current_regime"):
                return str(self._regime.current_regime)
        except Exception:
            pass
        return "UNKNOWN"

    @staticmethod
    def _rebuild_genome(original: Any, new_params: Dict[str, Any]) -> Any:
        """
        Reconstruct a genome from original + new params.
        Returns a deep copy with updated params.
        """
        try:
            clone = copy.deepcopy(original)
            if isinstance(clone, dict):
                if "params" in clone:
                    clone["params"] = new_params
                else:
                    clone.update(new_params)
            else:
                clone.params = new_params
            return clone
        except Exception:
            # Fallback: return a plain dict
            return {"params": new_params}

    # ── Delegation to base engine ─────────────────────────────────────────────

    def __getattr__(self, name: str) -> Any:
        """
        Transparently delegate any unknown attribute access to the wrapped
        base mutation engine.  This preserves full backward compatibility.
        """
        if name.startswith("_"):
            raise AttributeError(name)
        base = object.__getattribute__(self, "_base")
        if base is not None and hasattr(base, name):
            return getattr(base, name)
        raise AttributeError(
            f"'{type(self).__name__}' and its base engine have no attribute '{name}'"
        )

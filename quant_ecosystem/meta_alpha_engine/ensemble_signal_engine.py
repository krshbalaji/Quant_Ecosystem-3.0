"""
ensemble_signal_engine.py
Ensemble of heterogeneous signal models combined via regime-conditional blending.
Each ensemble member has a regime-specific weight learned from historical IC.

Architecture mirrors how Medallion blends sub-strategies:
  - Each "model" is a strategy type + feature rule combination
  - Weights are updated based on rolling IC per regime
  - Ensemble output is a weighted vote across all active models
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from quant_ecosystem.signal_factory.signal_generator_engine import RawSignal
from quant_ecosystem.signal_factory.signal_quality_engine import SignalQualityEngine
from quant_ecosystem.meta_alpha_engine.alpha_combination_engine import AlphaCombinationEngine, MetaSignal


# ---------------------------------------------------------------------------
# Model performance tracker
# ---------------------------------------------------------------------------

@dataclass
class ModelPerformance:
    """Tracks IC history per (model, regime) pair."""
    model_id: str
    regime: str
    ic_history: List[float] = field(default_factory=list)
    weight: float = 1.0
    last_updated: float = field(default_factory=time.time)

    def rolling_ic(self, window: int = 20) -> float:
        if not self.ic_history:
            return 0.0
        return float(np.mean(self.ic_history[-window:]))

    def update_ic(self, ic: float) -> None:
        self.ic_history.append(float(ic))
        if len(self.ic_history) > 200:
            self.ic_history = self.ic_history[-100:]
        self.last_updated = time.time()


# ---------------------------------------------------------------------------
# Ensemble member
# ---------------------------------------------------------------------------

@dataclass
class EnsembleMember:
    """One model in the ensemble."""
    model_id: str
    model_type: str          # ema_cross | rsi_threshold | macd_histogram | etc.
    strategy_ids: List[str]  # which strategy instances feed this model
    base_weight: float = 1.0
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "model_type": self.model_type,
            "strategy_ids": self.strategy_ids,
            "base_weight": self.base_weight,
            "enabled": self.enabled,
        }


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class EnsembleSignalEngine:
    """
    Regime-conditional weighted ensemble of signal models.

    How it works:
      1. Receive raw signals from all strategies
      2. Group signals by model_type
      3. Compute per-model meta-signal (via AlphaCombinationEngine)
      4. Apply regime-conditioned weights
      5. Blend into final ensemble signal per symbol

    Usage:
        ens = EnsembleSignalEngine()
        ens.register_member(EnsembleMember("trend_model", "ema_cross", ["trend_1", "trend_2"]))
        final = ens.generate(raw_signals, regime="TRENDING_BULL")
    """

    def __init__(
        self,
        quality_engine: Optional[SignalQualityEngine] = None,
        min_ensemble_agreement: float = 0.40,
        ic_weight_floor: float = 0.10,
        ic_weight_cap: float = 3.0,
        learning_rate: float = 0.10, **kwargs
    ) -> None:
        self._quality = quality_engine or SignalQualityEngine()
        self._combiner = AlphaCombinationEngine(method="ic_weighted", quality_engine=self._quality)
        self._members: Dict[str, EnsembleMember] = {}
        self._perf: Dict[str, ModelPerformance] = {}  # "{model_id}|{regime}"
        self._min_agreement = float(min_ensemble_agreement)
        self._ic_floor = float(ic_weight_floor)
        self._ic_cap = float(ic_weight_cap)
        self._lr = float(learning_rate)
        self._regime = "UNKNOWN"

    # ------------------------------------------------------------------
    # Member management
    # ------------------------------------------------------------------

    def register_member(self, member: EnsembleMember) -> None:
        self._members[member.model_id] = member

    def register_many(self, members: List[EnsembleMember]) -> None:
        for m in members:
            self.register_member(m)

    def disable_member(self, model_id: str) -> None:
        if model_id in self._members:
            self._members[model_id].enabled = False

    def enable_member(self, model_id: str) -> None:
        if model_id in self._members:
            self._members[model_id].enabled = True

    # ------------------------------------------------------------------
    # Main API
    # ------------------------------------------------------------------

    def update_regime(self, regime: str) -> None:
        self._regime = str(regime).upper()
        self._combiner.update_regime(regime)

    def generate(
        self,
        raw_signals: List[RawSignal],
        regime: Optional[str] = None,
        top_n: Optional[int] = None,
    ) -> List[MetaSignal]:
        """Produce ensemble meta-signals per symbol from raw signals."""
        if regime:
            self.update_regime(regime)

        if not self._members:
            # No ensemble config — pass through to combiner directly
            return self._combiner.combine(raw_signals)

        # Route signals to their model members
        model_signals: Dict[str, List[RawSignal]] = defaultdict(list)
        unrouted: List[RawSignal] = []

        strat_to_model = self._build_strategy_to_model_map()
        for sig in raw_signals:
            model_id = strat_to_model.get(sig.strategy_id)
            if model_id and self._members[model_id].enabled:
                model_signals[model_id].append(sig)
            else:
                unrouted.append(sig)

        # Per-model meta-signals
        model_meta: Dict[str, List[MetaSignal]] = defaultdict(list)
        for model_id, sigs in model_signals.items():
            if not sigs:
                continue
            meta_list = self._combiner.combine(sigs)
            for meta in meta_list:
                model_meta[meta.symbol].append((model_id, meta))

        # Add unrouted signals as raw signals
        if unrouted:
            for meta in self._combiner.combine(unrouted):
                model_meta[meta.symbol].append(("unrouted", meta))

        # Blend per symbol
        results: List[MetaSignal] = []
        for symbol, model_metas in model_meta.items():
            blended = self._blend_symbol(symbol, model_metas)
            if blended and blended.side != "HOLD":
                results.append(blended)

        results.sort(key=lambda m: m.combined_strength, reverse=True)
        return results[:top_n] if top_n else results

    def update_model_ic(self, model_id: str, ic: float, regime: Optional[str] = None) -> None:
        """Update a model's IC score for adaptive weight adjustment."""
        r = regime or self._regime
        key = f"{model_id}|{r}"
        if key not in self._perf:
            self._perf[key] = ModelPerformance(model_id=model_id, regime=r)
        self._perf[key].update_ic(ic)
        # Update model weight
        perf = self._perf[key]
        rolling = perf.rolling_ic()
        new_weight = max(self._ic_floor, min(self._ic_cap, 1.0 + rolling * 10))
        member = self._members.get(model_id)
        if member:
            member.base_weight = (
                member.base_weight * (1 - self._lr) + new_weight * self._lr
            )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_strategy_to_model_map(self) -> Dict[str, str]:
        mapping: Dict[str, str] = {}
        for mid, member in self._members.items():
            for sid in member.strategy_ids:
                mapping[sid] = mid
        return mapping

    def _blend_symbol(
        self,
        symbol: str,
        model_metas: List[Tuple[str, MetaSignal]],
    ) -> Optional[MetaSignal]:
        """Blend model-level meta-signals into a single ensemble signal."""
        if not model_metas:
            return None

        weighted_scores: Dict[str, float] = {}  # side → weighted sum
        total_weight = 0.0

        for model_id, meta in model_metas:
            member = self._members.get(model_id)
            base_w = member.base_weight if member else 1.0
            # Regime IC weight
            perf_key = f"{model_id}|{self._regime}"
            perf = self._perf.get(perf_key)
            ic_w = max(self._ic_floor, 1.0 + (perf.rolling_ic() * 5)) if perf else 1.0
            weight = base_w * ic_w * meta.agreement_rate
            score = _side_score_meta(meta.side) * meta.combined_strength * weight
            weighted_scores[meta.side] = weighted_scores.get(meta.side, 0.0) + score
            total_weight += weight

        if total_weight == 0:
            return None

        net = sum(weighted_scores.values()) / total_weight
        if net > 0.05:
            side = "BUY"
        elif net < -0.05:
            side = "SELL"
        else:
            return None

        strength = min(1.0, abs(net))
        n_agree = sum(1 for _, m in model_metas if m.side == side)
        agreement = n_agree / len(model_metas)

        if agreement < self._min_agreement:
            return None

        return MetaSignal(
            symbol=symbol,
            side=side,
            combined_strength=round(strength, 6),
            n_contributors=len(model_metas),
            agreement_rate=round(agreement, 4),
            method=f"ensemble_{self._regime.lower()}",
            source_signals=[m.to_dict() for _, m in model_metas],
            metadata={"regime": self._regime, "total_weight": round(total_weight, 4)},
        )

    def model_weights(self) -> Dict[str, float]:
        return {mid: m.base_weight for mid, m in self._members.items()}

    def stats(self) -> Dict[str, Any]:
        return {
            "members": len(self._members),
            "active_members": sum(1 for m in self._members.values() if m.enabled),
            "regime": self._regime,
            "weights": self.model_weights(),
        }


def _side_score_meta(side: str) -> float:
    return 1.0 if side == "BUY" else -1.0 if side == "SELL" else 0.0

"""Mutation pipeline for Strategy Lab candidates."""

from __future__ import annotations

import copy
import random
from typing import Dict, Iterable, List, Optional


class MutationPipeline:
    """Generates controlled mutations using existing mutation engine when available."""

    def __init__(self, mutation_layer=None, seed: Optional[int] = None):
        self.mutation_layer = mutation_layer
        self._rng = random.Random(seed)
        self._indicator_swaps = {
            "macd": "aroon",
            "aroon": "macd",
            "rsi": "stochastic",
            "stochastic": "rsi",
            "bollinger": "keltner",
            "keltner": "bollinger",
            "ema": "vwap",
            "vwap": "ema",
        }
        self._timeframes = ["5m", "15m", "1h", "1d"]

    def mutate(self, base_strategies: Iterable[Dict], variants_per_base: int = 10) -> List[Dict]:
        """Create mutations for each base strategy."""
        bases = [dict(item) for item in base_strategies if item.get("id")]
        if not bases:
            return []

        # Use existing mutation engine when enabled.
        if self.mutation_layer and hasattr(self.mutation_layer, "is_enabled") and self.mutation_layer.is_enabled():
            try:
                produced = self.mutation_layer.run(bases)
                if produced:
                    return [self._normalize_external(candidate) for candidate in produced]
            except Exception:
                pass

        out: List[Dict] = []
        for base in bases:
            for idx in range(max(1, int(variants_per_base))):
                out.append(self._local_mutation(base, idx))
        return out

    def _local_mutation(self, base: Dict, idx: int) -> Dict:
        item = copy.deepcopy(base)
        item["id"] = f"{base.get('id')}_m{idx + 1}"
        item["name"] = item["id"]
        item["stage"] = "RESEARCH"
        item["active"] = False
        params = dict(item.get("parameters", {}))

        # Parameter mutation.
        for key in list(params.keys()):
            if isinstance(params[key], (int, float)) and self._rng.random() < 0.7:
                drift = self._rng.uniform(0.9, 1.1)
                params[key] = round(float(params[key]) * drift, 4)
        item["parameters"] = params

        # Indicator mutation.
        indicators = list(item.get("indicators", []))
        if indicators:
            i = self._rng.randrange(len(indicators))
            indicators[i] = self._indicator_swaps.get(indicators[i], indicators[i])
        item["indicators"] = indicators

        # Timeframe mutation.
        if self._rng.random() < 0.5:
            item["timeframe"] = self._rng.choice(self._timeframes)

        # Risk model mutation.
        risk_model = str(item.get("risk_model", "fixed_risk"))
        if self._rng.random() < 0.5:
            risk_model = self._rng.choice(["fixed_risk", "atr_risk", "vol_target", "kelly_fractional"])
        item["risk_model"] = risk_model

        # Logic mutation.
        item["entry_logic"] = self._mutate_logic(str(item.get("entry_logic", "")))
        item["exit_logic"] = self._mutate_logic(str(item.get("exit_logic", "")))

        meta = dict(item.get("metadata", {}))
        meta["mutation_origin"] = str(base.get("id"))
        item["metadata"] = meta
        return item

    def _mutate_logic(self, logic: str) -> str:
        out = logic
        replacements = [
            ("RSI > 70", "RSI > 65"),
            ("RSI < 30", "RSI < 35"),
            ("ema_fast_cross_ema_slow", "vwap_cross_filter"),
            ("atr_filter", "volume_filter"),
        ]
        for src, dst in replacements:
            if src.lower() in out.lower() and self._rng.random() < 0.5:
                out = out.replace(src, dst)
        return out

    def _normalize_external(self, candidate: Dict) -> Dict:
        dna = candidate.get("dna", {}) if isinstance(candidate.get("dna"), dict) else {}
        metrics = dict(candidate.get("metrics", {}))
        cid = candidate.get("id") or f"mut_{self._rng.randint(100000, 999999)}"
        return {
            "id": cid,
            "name": cid,
            "strategy_type": candidate.get("strategy_type", "momentum"),
            "category": candidate.get("category", "systematic"),
            "family": candidate.get("family", candidate.get("category", "systematic")),
            "asset_class": candidate.get("asset_class", dna.get("asset_class", "stocks")),
            "timeframe": candidate.get("timeframe", dna.get("timeframe", "5m")),
            "indicators": list(dna.get("indicators", [])),
            "entry_logic": dna.get("entry_logic", "generated"),
            "exit_logic": dna.get("exit_logic", "generated"),
            "risk_model": candidate.get("risk_model", "atr_risk"),
            "parameters": dict(dna.get("parameters", {})),
            "stage": "RESEARCH",
            "active": False,
            "metrics": metrics,
            "metadata": {"mutation_origin": candidate.get("path", "mutation_engine")},
        }


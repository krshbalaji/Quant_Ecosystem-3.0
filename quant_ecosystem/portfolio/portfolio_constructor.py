from __future__ import annotations

from typing import Dict, List


class PortfolioConstructor:
    """
    Converts aggregated symbol-level signals and strategy weights into a
    target exposure map expressed as fraction of portfolio equity.
    """

    def __init__(self, capital_allocator=None, **kwargs):
        self.capital_allocator = capital_allocator

    def build_target_portfolio(
        self,
        aggregated_signals: List[Dict],
        strategy_weights: Dict[str, float],
        equity: float,
    ) -> Dict[str, float]:
        """
        Returns a mapping symbol -> target weight (e.g. 0.25 == 25% of equity).
        """
        if not aggregated_signals or equity <= 0:
            return {}

        # For this initial implementation we treat all strategies equally at
        # the symbol level and rely on CapitalAllocator at the strategy layer.
        targets: Dict[str, float] = {}
        for sig in aggregated_signals:
            symbol = sig["symbol"]
            side = sig["side"]
            confidence = float(sig.get("confidence", 0.0))
            if confidence <= 0:
                continue
            base_weight = confidence  # 0..1
            weight = base_weight if side == "BUY" else -base_weight
            targets[symbol] = targets.get(symbol, 0.0) + weight

        # Normalise weights to avoid over-allocation beyond 100% gross.
        gross = sum(abs(w) for w in targets.values())
        if gross > 1.0:
            scale = 1.0 / gross
            for k in list(targets.keys()):
                targets[k] *= scale

        return targets


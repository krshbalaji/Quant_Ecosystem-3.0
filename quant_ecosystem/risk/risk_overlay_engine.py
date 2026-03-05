from __future__ import annotations

from typing import Dict


class RiskOverlayEngine:
    """
    Applies portfolio-level risk constraints to target weights.
    """

    def __init__(self, risk_engine, portfolio_engine, state):
        self.risk_engine = risk_engine
        self.portfolio_engine = portfolio_engine
        self.state = state

    def apply(self, target_portfolio: Dict[str, float]) -> Dict[str, float]:
        """
        Scale the proposed portfolio to respect max_portfolio_risk and
        max_symbol_risk. Returns a new mapping symbol -> weight.
        """
        if not target_portfolio:
            return {}

        # Cap total gross exposure by max_portfolio_risk.
        max_portfolio = self.risk_engine.max_portfolio_risk / 100.0
        gross = sum(abs(w) for w in target_portfolio.values())
        scaled = dict(target_portfolio)
        if gross > max_portfolio and gross > 0:
            scale = max_portfolio / gross
            for k in list(scaled.keys()):
                scaled[k] *= scale

        # Cap per-symbol risk; if any symbol weight exceeds the per-symbol cap,
        # scale it back.
        max_symbol = self.risk_engine.max_symbol_risk / 100.0
        for sym, w in list(scaled.items()):
            if abs(w) > max_symbol and max_symbol > 0:
                scaled[sym] = max_symbol if w > 0 else -max_symbol

        return scaled


"""
Portfolio allocation engine for multi-strategy institutional execution.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class PortfolioEngine:

    def __init__(self):
        self.capital = 100000.0
        # Changed: allocations now per strategy per symbol
        self.allocations = {}  # {strategy_id: {symbol: capital}}
        self.performance = {}  # {market: pnl}
        self.market_exposure = {}  # {market: total_exposure}
        self.correlation_matrix = {}  # For correlation control

    def allocate(self, strategy_scores, market_intelligence=None):
        """
        Allocate capital based on strategy scores, market volatility, and correlation.
        strategy_scores: {strategy_id: score}
        market_intelligence: {symbol: {market, volatility, confidence}}
        """
        if not isinstance(strategy_scores, dict):
            return {}

        # Get market intelligence for correlation and volatility adjustment
        market_data = market_intelligence or {}
        
        # Calculate adjusted scores based on market conditions
        adjusted_scores = {}
        for strategy, score in strategy_scores.items():
            base_score = max(0.0, float(score or 0.0))
            
            # Apply market-based adjustments
            market_multiplier = 1.0
            for symbol_data in market_data.values():
                volatility = symbol_data.get("volatility", 0.0)
                confidence = symbol_data.get("confidence", 0.5)
                # Reduce allocation in high volatility, increase with confidence
                market_multiplier *= (1.0 - volatility * 0.5) * confidence
            
            adjusted_scores[strategy] = base_score * market_multiplier

        total_score = sum(adjusted_scores.values())
        if total_score == 0.0:
            self.allocations = {}
            return {}

        # Allocate across strategies and symbols
        allocations = {}
        symbols_per_strategy = self._distribute_symbols_to_strategies(list(market_data.keys()), list(adjusted_scores.keys()))
        
        for strategy, symbols in symbols_per_strategy.items():
            allocations[strategy] = {}
            strategy_weight = adjusted_scores[strategy] / total_score
            
            for symbol in symbols:
                symbol_weight = 1.0 / len(symbols)  # Equal weight per symbol
                allocations[strategy][symbol] = strategy_weight * symbol_weight * self.capital

        self.allocations = allocations
        
        # Update market exposure
        self._update_market_exposure(market_data)
        
        return allocations

    def _distribute_symbols_to_strategies(self, symbols, strategies):
        """Distribute symbols to strategies with correlation control."""
        if not symbols or not strategies:
            return {strat: symbols for strat in strategies}
        
        # Simple distribution: each strategy gets all symbols
        # Advanced: could implement correlation-based distribution
        return {strat: symbols.copy() for strat in strategies}

    def _update_market_exposure(self, market_data):
        """Update total exposure per market."""
        self.market_exposure = {}
        for strategy_alloc in self.allocations.values():
            for symbol, capital in strategy_alloc.items():
                market = "UNKNOWN"
                for symbol_data in market_data.values():
                    if symbol_data.get("symbol") == symbol:
                        market = symbol_data.get("market", "UNKNOWN")
                        break
                
                self.market_exposure[market] = self.market_exposure.get(market, 0.0) + capital

    def get_total_exposure(self):
        """Get total exposure across all markets."""
        return sum(self.market_exposure.values())

    def get_market_exposure(self, market):
        """Get exposure for specific market."""
        return self.market_exposure.get(market, 0.0)

    def record_performance(self, strategy_id, symbol, pnl):
        """Record performance per symbol."""
        if not strategy_id or not symbol:
            return
            
        market = "UNKNOWN"
        if symbol.startswith("FX:"):
            market = "FX"
        elif symbol.startswith("NSE:"):
            market = "EQUITY"
        elif "USDT" in symbol or "BTC" in symbol or "ETH" in symbol:
            market = "CRYPTO"
            
        self.performance[market] = self.performance.get(market, 0.0) + pnl

    def get_market_performance(self, market):
        """Get performance for specific market."""
        return self.performance.get(market, 0.0)

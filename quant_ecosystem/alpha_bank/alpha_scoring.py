"""
alpha_scoring.py — Quant Ecosystem 3.0
=======================================

Fitness scoring and ranking logic for strategies.

Provides multiple scoring methods:
- Composite Fitness Score (default)
- Sharpe-only ranking
- Risk-adjusted returns
- Multi-period evaluation
- Drawdown-penalized scores

Supports different market regimes and symbols.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class ScoringMetric(Enum):
    """Available scoring metrics."""
    
    FITNESS = "fitness_score"           # Composite score
    SHARPE = "sharpe_ratio"             # Risk-adjusted returns
    SORTINO = "sortino_ratio"           # Downside risk
    CALMAR = "calmar_ratio"             # Return per unit of max drawdown
    ANNUAL_RETURN = "annual_return"     # Total return
    WIN_RATE = "win_rate"               # % winning trades
    PROFIT_FACTOR = "profit_factor"     # Gross profit / gross loss


class AlphaScorer:
    """
    Scoring engine for strategy evaluation.
    
    Calculates fitness scores based on multiple performance metrics,
    with configurable weights and thresholds.
    
    Parameters
    ----------
    sharpe_weight : float, default=0.40
        Weight for Sharpe ratio in composite fitness.
    sortino_weight : float, default=0.30
        Weight for Sortino ratio.
    return_weight : float, default=0.20
        Weight for annual return.
    win_rate_weight : float, default=0.10
        Weight for win rate.
    penalize_drawdown : bool, default=True
        Apply penalty for large drawdowns.
    consistency_bonus : bool, default=True
        Bonus for consistent performance.
    regime_aware : bool, default=False
        Adjust scores based on market regime (experimental).
    
    Examples
    --------
    >>> scorer = AlphaScorer()
    >>> 
    >>> metrics = {
    ...     "sharpe_ratio": 1.8,
    ...     "sortino_ratio": 2.1,
    ...     "annual_return": 0.42,
    ...     "max_drawdown": 0.12,
    ...     "win_rate": 0.58,
    ... }
    >>> 
    >>> fitness = scorer.calculate_fitness(metrics)
    >>> print(f"Fitness: {fitness:.4f}")
    """
    
    def __init__(
        self,
        sharpe_weight: float = 0.40,
        sortino_weight: float = 0.30,
        return_weight: float = 0.20,
        win_rate_weight: float = 0.10,
        penalize_drawdown: bool = True,
        consistency_bonus: bool = True,
        regime_aware: bool = False,
    ) -> None:
        # Validate weights
        total_weight = sharpe_weight + sortino_weight + return_weight + win_rate_weight
        if abs(total_weight - 1.0) > 0.001:
            raise ValueError(f"Weights must sum to 1.0, got {total_weight}")
        
        self.sharpe_weight = sharpe_weight
        self.sortino_weight = sortino_weight
        self.return_weight = return_weight
        self.win_rate_weight = win_rate_weight
        self.penalize_drawdown = penalize_drawdown
        self.consistency_bonus = consistency_bonus
        self.regime_aware = regime_aware
        
        logger.info("AlphaScorer initialized with weights: sharpe=%.2f, sortino=%.2f, return=%.2f, wr=%.2f",
                   sharpe_weight, sortino_weight, return_weight, win_rate_weight)
    
    # -----------------------------------------------------------------------
    # Fitness Scoring
    # -----------------------------------------------------------------------
    
    def calculate_fitness(
        self,
        metrics: Dict[str, float],
        regime: Optional[str] = None,
    ) -> float:
        """
        Calculate composite fitness score.
        
        Parameters
        ----------
        metrics : dict
            Performance metrics dict.
        regime : str, optional
            Market regime (bullish, bearish, range-bound).
        
        Returns
        -------
        float
            Fitness score (0 to 1).
        
        Examples
        --------
        >>> metrics = {"sharpe_ratio": 1.5, "sortino_ratio": 2.0, ...}
        >>> fitness = scorer.calculate_fitness(metrics)
        """
        try:
            # Normalize individual components
            sharpe_norm = self._normalize_sharpe(metrics.get("sharpe_ratio", 0))
            sortino_norm = self._normalize_sortino(metrics.get("sortino_ratio", 0))
            return_norm = self._normalize_return(metrics.get("annual_return", 0))
            win_rate_norm = metrics.get("win_rate", 0)  # Already 0-1
            
            # Weighted composite
            fitness = (
                self.sharpe_weight * sharpe_norm +
                self.sortino_weight * sortino_norm +
                self.return_weight * return_norm +
                self.win_rate_weight * win_rate_norm
            )
            
            # Apply drawdown penalty
            if self.penalize_drawdown:
                fitness = self._apply_drawdown_penalty(fitness, metrics.get("max_drawdown", 0))
            
            # Apply consistency bonus
            if self.consistency_bonus:
                fitness = self._apply_consistency_bonus(fitness, metrics)
            
            # Regime adjustment
            if self.regime_aware and regime:
                fitness = self._adjust_for_regime(fitness, regime, metrics)
            
            return round(max(0, min(1, fitness)), 4)
        
        except Exception as exc:
            logger.error("AlphaScorer.calculate_fitness failed: %s", exc)
            return 0.0
    
    def rank_by_metric(
        self,
        strategies: List[Dict[str, Any]],
        metric: ScoringMetric = ScoringMetric.FITNESS,
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Rank strategies by a specific metric.
        
        Parameters
        ----------
        strategies : list
            Strategy records with metrics.
        metric : ScoringMetric
            Ranking metric.
        
        Returns
        -------
        list
            (strategy, score) tuples sorted by score descending.
        
        Examples
        --------
        >>> ranked = scorer.rank_by_metric(strategies, ScoringMetric.SHARPE)
        >>> for strategy, score in ranked[:10]:
        ...     print(f"{strategy['genome_id']}: {score:.2f}")
        """
        results = []
        
        for strategy in strategies:
            metrics = strategy.get("metrics", {})
            
            if metric == ScoringMetric.FITNESS:
                score = metrics.get("fitness_score", 0)
            elif metric == ScoringMetric.SHARPE:
                score = metrics.get("sharpe_ratio", 0)
            elif metric == ScoringMetric.SORTINO:
                score = metrics.get("sortino_ratio", 0)
            elif metric == ScoringMetric.CALMAR:
                score = metrics.get("calmar_ratio", 0)
            elif metric == ScoringMetric.ANNUAL_RETURN:
                score = metrics.get("annual_return", 0)
            elif metric == ScoringMetric.WIN_RATE:
                score = metrics.get("win_rate", 0)
            elif metric == ScoringMetric.PROFIT_FACTOR:
                score = metrics.get("profit_factor", 0)
            else:
                score = 0
            
            results.append((strategy, score))
        
        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results
    
    def score_for_regime(
        self,
        metrics: Dict[str, float],
        regime: str,
    ) -> float:
        """
        Calculate score optimized for a specific regime.
        
        Regimes:
        - bullish: Weight returns higher
        - bearish: Weight Sharpe/Sortino higher, penalize drawdown more
        - range_bound: Weight win_rate higher
        
        Parameters
        ----------
        metrics : dict
            Performance metrics.
        regime : str
            Market regime (bullish, bearish, range_bound).
        
        Returns
        -------
        float
            Regime-adjusted fitness score.
        """
        try:
            if regime == "bullish":
                # Favor returns
                w = {
                    "sharpe": 0.25,
                    "sortino": 0.20,
                    "return": 0.40,
                    "win_rate": 0.15,
                }
            elif regime == "bearish":
                # Favor risk-adjusted returns and consistency
                w = {
                    "sharpe": 0.45,
                    "sortino": 0.35,
                    "return": 0.10,
                    "win_rate": 0.10,
                }
            elif regime == "range_bound":
                # Favor win rate
                w = {
                    "sharpe": 0.25,
                    "sortino": 0.25,
                    "return": 0.25,
                    "win_rate": 0.25,
                }
            else:
                # Unknown regime, use balanced weights
                w = {
                    "sharpe": 0.35,
                    "sortino": 0.30,
                    "return": 0.20,
                    "win_rate": 0.15,
                }
            
            # Calculate weighted score
            fitness = (
                w["sharpe"] * self._normalize_sharpe(metrics.get("sharpe_ratio", 0)) +
                w["sortino"] * self._normalize_sortino(metrics.get("sortino_ratio", 0)) +
                w["return"] * self._normalize_return(metrics.get("annual_return", 0)) +
                w["win_rate"] * metrics.get("win_rate", 0)
            )
            
            # Apply regime-specific penalties
            if regime == "bearish":
                # Higher drawdown penalty
                fitness *= max(0.5, 1.0 - metrics.get("max_drawdown", 0))
            
            return round(max(0, min(1, fitness)), 4)
        
        except Exception as exc:
            logger.error("AlphaScorer.score_for_regime failed: %s", exc)
            return 0.0
    
    # -----------------------------------------------------------------------
    # Viability Checks
    # -----------------------------------------------------------------------
    
    def is_viable(
        self,
        metrics: Dict[str, float],
        min_fitness: float = 0.5,
        min_sharpe: float = 0.0,
        max_drawdown: float = 0.5,
        min_trades: int = 10,
    ) -> bool:
        """
        Check if strategy is viable based on criteria.
        
        Parameters
        ----------
        metrics : dict
            Performance metrics.
        min_fitness : float
            Minimum fitness score.
        min_sharpe : float
            Minimum Sharpe ratio.
        max_drawdown : float
            Maximum acceptable drawdown.
        min_trades : int
            Minimum number of trades.
        
        Returns
        -------
        bool
            True if strategy meets all criteria.
        """
        try:
            # Check each criterion
            fitness = metrics.get("fitness_score", 0)
            if fitness < min_fitness:
                return False
            
            sharpe = metrics.get("sharpe_ratio", 0)
            if sharpe < min_sharpe:
                return False
            
            drawdown = metrics.get("max_drawdown", 0)
            if drawdown > max_drawdown:
                return False
            
            trades = metrics.get("num_trades", 0)
            if trades < min_trades:
                return False
            
            return True
        
        except Exception:
            return False
    
    # -----------------------------------------------------------------------
    # Comparative Analysis
    # -----------------------------------------------------------------------
    
    def compare_strategies(
        self,
        strategy1: Dict[str, Any],
        strategy2: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Compare two strategies across multiple metrics.
        
        Parameters
        ----------
        strategy1, strategy2 : dict
            Strategy records.
        
        Returns
        -------
        dict
            Comparison results with winner and detailed metrics.
        """
        try:
            m1 = strategy1.get("metrics", {})
            m2 = strategy2.get("metrics", {})
            
            comparison = {
                "strategy1": strategy1.get("genome_id"),
                "strategy2": strategy2.get("genome_id"),
                "metrics": {},
            }
            
            metrics_to_compare = [
                "fitness_score", "sharpe_ratio", "sortino_ratio",
                "annual_return", "max_drawdown", "win_rate"
            ]
            
            winner_count_1 = 0
            winner_count_2 = 0
            
            for metric in metrics_to_compare:
                val1 = m1.get(metric, 0)
                val2 = m2.get(metric, 0)
                
                # For drawdown, lower is better
                if metric == "max_drawdown":
                    better = val1 < val2
                else:
                    better = val1 > val2
                
                comparison["metrics"][metric] = {
                    "strategy1": round(val1, 4),
                    "strategy2": round(val2, 4),
                    "winner": "strategy1" if better else "strategy2",
                }
                
                if better:
                    winner_count_1 += 1
                else:
                    winner_count_2 += 1
            
            # Overall winner
            if winner_count_1 > winner_count_2:
                comparison["overall_winner"] = "strategy1"
            elif winner_count_2 > winner_count_1:
                comparison["overall_winner"] = "strategy2"
            else:
                comparison["overall_winner"] = "tie"
            
            return comparison
        
        except Exception as exc:
            logger.error("AlphaScorer.compare_strategies failed: %s", exc)
            return {}
    
    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------
    
    @staticmethod
    def _normalize_sharpe(sharpe: float) -> float:
        """Normalize Sharpe ratio to 0-1 range. Sharpe > 3 is excellent."""
        return min(sharpe / 3.0, 1.0)
    
    @staticmethod
    def _normalize_sortino(sortino: float) -> float:
        """Normalize Sortino ratio to 0-1 range. Sortino > 4 is excellent."""
        return min(sortino / 4.0, 1.0)
    
    @staticmethod
    def _normalize_return(annual_return: float) -> float:
        """Normalize annual return to 0-1 range. Return > 100% is excellent."""
        return min(annual_return / 1.0, 1.0)
    
    @staticmethod
    def _apply_drawdown_penalty(fitness: float, max_drawdown: float) -> float:
        """Apply penalty for drawdown. Max 50% penalty."""
        if max_drawdown <= 0:
            return fitness
        
        penalty = min(max_drawdown / 2.0, 0.5)  # Cap at 50% penalty
        return fitness * (1.0 - penalty)
    
    @staticmethod
    def _apply_consistency_bonus(fitness: float, metrics: Dict[str, float]) -> float:
        """Apply bonus for consistency if available."""
        try:
            # If strategy has recovery_days metric, reward quick recovery
            recovery_days = metrics.get("recovery_days", 0)
            
            if recovery_days > 0 and recovery_days < 30:
                # Bonus: recovered quickly after drawdown
                bonus = 0.05 * (1.0 - recovery_days / 30.0)
                return fitness + bonus
            
            return fitness
        except Exception:
            return fitness
    
    @staticmethod
    def _adjust_for_regime(fitness: float, regime: str, metrics: Dict[str, float]) -> float:
        """Adjust fitness based on market regime."""
        try:
            if regime == "bullish" and metrics.get("annual_return", 0) > 0.5:
                # Bonus for high returns in bull market
                return fitness * 1.1
            elif regime == "bearish" and metrics.get("max_drawdown", 0) < 0.1:
                # Bonus for low drawdown in bear market
                return fitness * 1.1
            
            return fitness
        except Exception:
            return fitness

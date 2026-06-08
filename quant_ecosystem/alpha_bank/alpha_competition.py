"""
alpha_competition.py — Quant Ecosystem 3.0
==========================================

Strategy competition, selection, and tournament logic.

Provides:
- Strategy competition/bracketing
- Selection for mutation and crossover
- Tournament-based elimination
- Portfolio construction from top strategies
- Strategy diversity tracking

Used by AlphaEvolutionEngine and StrategySelector.
"""

from __future__ import annotations

import logging
import random
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


from dataclasses import dataclass, field

@dataclass
class TournamentRound:
    round_num: int
    matchups: List[Tuple[Dict[str, Any], Dict[str, Any]]]
    winners: List[Dict[str, Any]] = field(default_factory=list)


class AlphaCompetition:
    """
    Strategy competition and selection engine.
    
    Features:
    - Tournament-style strategy elimination
    - Elite selection for breeding
    - Diversity maintenance
    - Portfolio construction from best strategies
    - Strategy clustering by family
    
    Parameters
    ----------
    bank : AlphaBank
        Reference to the alpha bank for strategy data.
    tournament_size : int, default=8
        Number of strategies per tournament round.
    elite_fraction : float, default=0.1
        Fraction of strategies to keep as elite (for breeding).
    diversity_target : float, default=0.5
        Target diversity score (0=identical, 1=maximally diverse).
    
    Examples
    --------
    >>> competition = AlphaCompetition(bank)
    >>> 
    >>> # Run tournament
    >>> tournament = competition.run_tournament(num_rounds=3)
    >>> print(f"Tournament winner: {tournament.winners[-1][0]['genome_id']}")
    >>> 
    >>> # Select strategies for breeding
    >>> breeders = competition.select_for_breeding(num_parents=10)
    >>> 
    >>> # Build portfolio
    >>> portfolio = competition.build_portfolio(num_strategies=5)
    """
    
    def __init__(
        self,
        bank: Any = None,
        tournament_size: int = 8,
        elite_fraction: float = 0.1,
        diversity_target: float = 0.5,
    ) -> None:
        self.bank = bank
        self.tournament_size = tournament_size
        self.elite_fraction = elite_fraction
        self.diversity_target = diversity_target
        
        logger.info(
            "AlphaCompetition initialized (tournament_size=%d, elite=%.1f%%)",
            tournament_size, elite_fraction * 100
        )
    
    # -----------------------------------------------------------------------
    # Tournament Selection
    # -----------------------------------------------------------------------
    
    def run_tournament(
        self,
        strategies: Optional[List[Dict[str, Any]]] = None,
        num_rounds: int = 3,
        metric: str = "fitness_score",
    ) -> TournamentRound:
        """
        Run elimination tournament to find best strategy.
        
        Parameters
        ----------
        strategies : list, optional
            Strategies to compete. If None, uses all from bank.
        num_rounds : int
            Number of tournament rounds.
        metric : str
            Metric to use for comparisons.
        
        Returns
        -------
        TournamentRound
            Final tournament results with winner.
        
        Examples
        --------
        >>> tournament = competition.run_tournament(num_rounds=3)
        >>> winner = tournament.winners[-1][0]
        >>> print(f"Champion: {winner['genome_id']}")
        """
        try:
            if strategies is None:
                if self.bank:
                    strategies = self.bank.rank_strategies()
                else:
                    return TournamentRound(round_num=0, matchups=[])
            
            if not strategies:
                return TournamentRound(round_num=0, matchups=[])
            
            # Start tournament
            current_round = strategies
            all_rounds = []
            
            for round_num in range(num_rounds):
                matchups = []
                winners = []
                
                # Pair strategies
                for i in range(0, len(current_round) - 1, 2):
                    s1 = current_round[i]
                    s2 = current_round[i + 1]
                    
                    matchups.append((s1, s2))
                    
                    # Determine winner
                    winner = self._compare_strategies(s1, s2, metric)
                    winners.append(winner)
                
                # Handle odd number
                if len(current_round) % 2 == 1:
                    winners.append(current_round[-1])
                
                round_result = TournamentRound(
                    round_num=round_num,
                    matchups=matchups,
                    winners=winners
                )
                all_rounds.append(round_result)
                
                current_round = winners
                
                logger.info(
                    "Tournament round %d: %d matchups, %d winners",
                    round_num + 1, len(matchups), len(winners)
                )
            
            return all_rounds[-1] if all_rounds else TournamentRound(0, [])
        
        except Exception as exc:
            logger.error("AlphaCompetition.run_tournament failed: %s", exc)
            return TournamentRound(round_num=0, matchups=[])
    
    # -----------------------------------------------------------------------
    # Selection for Breeding
    # -----------------------------------------------------------------------
    
    def select_for_breeding(
        self,
        num_parents: int = 10,
        diversity_weight: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """
        Select strategies for breeding (mutation/crossover).
        
        Selection balances fitness and diversity:
        - High fitness strategies: more likely to breed
        - Diverse strategies: ensure genetic variety
        
        Parameters
        ----------
        num_parents : int
            Number of breeding candidates.
        diversity_weight : float
            Weight for diversity (0=fitness-only, 1=diversity-only).
        
        Returns
        -------
        list
            Selected breeding strategies.
        
        Examples
        --------
        >>> parents = competition.select_for_breeding(num_parents=20)
        >>> # Mutate each parent to create offspring
        >>> offspring = [mutation_engine.mutate(p) for p in parents]
        """
        try:
            if not self.bank:
                return []
            
            # Get top strategies
            top = self.bank.rank_strategies()
            if not top:
                return []
            
            # Score each by fitness + diversity
            candidates = []
            for i, strategy in enumerate(top):
                fitness = strategy.get("metrics", {}).get("fitness_score", 0)
                diversity = self._calculate_diversity(strategy, top[:100])
                
                # Combined score
                score = (1.0 - diversity_weight) * fitness + diversity_weight * diversity
                
                candidates.append((strategy, score))
            
            # Sort by combined score
            candidates.sort(key=lambda x: x[1], reverse=True)
            
            # Select top num_parents
            parents = [c[0] for c in candidates[:num_parents]]
            
            logger.info(
                "AlphaCompetition.select_for_breeding: selected %d parents",
                len(parents)
            )
            
            return parents
        
        except Exception as exc:
            logger.error("AlphaCompetition.select_for_breeding failed: %s", exc)
            return []
    
    def select_elite(self, fraction: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Select elite strategies (top performers).
        
        Parameters
        ----------
        fraction : float, optional
            Fraction of total strategies. Defaults to self.elite_fraction.
        
        Returns
        -------
        list
            Elite strategies.
        """
        try:
            if not self.bank:
                return []
            
            if fraction is None:
                fraction = self.elite_fraction
            
            total = self.bank._storage.count_strategies()
            elite_count = max(1, int(total * fraction))
            
            elite = self.bank.rank_strategies()[:elite_count]
            
            logger.info(
                "AlphaCompetition.select_elite: %d strategies (%.1f%% of %d total)",
                len(elite), fraction * 100, total
            )
            
            return elite
        
        except Exception as exc:
            logger.error("AlphaCompetition.select_elite failed: %s", exc)
            return []
    
    # -----------------------------------------------------------------------
    # Portfolio Construction
    # -----------------------------------------------------------------------
    
    def build_portfolio(
        self,
        num_strategies: int = 5,
        allocation_method: str = "equal_weight",
        metric: str = "fitness_score",
    ) -> Dict[str, Any]:
        """
        Build a portfolio from top strategies.
        
        Parameters
        ----------
        num_strategies : int
            Number of strategies in portfolio.
        allocation_method : str
            How to allocate capital (equal_weight, fitness_weighted, risk_parity).
        metric : str
            Ranking metric.
        
        Returns
        -------
        dict
            Portfolio definition with strategies and allocations.
        
        Examples
        --------
        >>> portfolio = competition.build_portfolio(num_strategies=5)
        >>> for strat, weight in zip(portfolio['strategies'], portfolio['weights']):
        ...     print(f"{strat['genome_id']}: {weight:.1%}")
        """
        try:
            if not self.bank:
                return {"strategies": [], "weights": [], "total_weight": 0}
            
            # Select strategies
            strategies = self.bank.get_top_strategies(
                limit=num_strategies,
                metric=metric
            )
            
            if not strategies:
                return {"strategies": [], "weights": [], "total_weight": 0}
            
            # Calculate allocations
            weights = self._calculate_allocations(
                strategies,
                method=allocation_method
            )
            
            portfolio = {
                "strategies": strategies,
                "weights": weights,
                "total_weight": sum(weights),
                "num_strategies": len(strategies),
                "allocation_method": allocation_method,
                "metrics": {
                    "avg_fitness": sum(s.get("metrics", {}).get("fitness_score", 0) for s in strategies) / len(strategies),
                    "avg_sharpe": sum(s.get("metrics", {}).get("sharpe_ratio", 0) for s in strategies) / len(strategies),
                    "min_drawdown": min(s.get("metrics", {}).get("max_drawdown", 0) for s in strategies),
                },
            }
            
            logger.info(
                "AlphaCompetition.build_portfolio: %d strategies, avg_fitness=%.3f",
                len(strategies), portfolio["metrics"]["avg_fitness"]
            )
            
            return portfolio
        
        except Exception as exc:
            logger.error("AlphaCompetition.build_portfolio failed: %s", exc)
            return {"strategies": [], "weights": [], "total_weight": 0}
    
    # -----------------------------------------------------------------------
    # Diversity Tracking
    # -----------------------------------------------------------------------
    
    def measure_diversity(
        self,
        strategies: Optional[List[Dict[str, Any]]] = None,
        sample_size: int = 100,
    ) -> float:
        """
        Measure portfolio diversity.
        
        Diversity = (1 - avg_correlation) / 2
        
        Parameters
        ----------
        strategies : list, optional
            Strategies to measure. Uses top 100 if None.
        sample_size : int
            Sample size for calculation.
        
        Returns
        -------
        float
            Diversity score (0=identical, 1=maximally diverse).
        """
        try:
            if strategies is None:
                if self.bank:
                    strategies = self.bank.rank_strategies()[:sample_size]
                else:
                    return 0.0

            if strategies is None:
                return 0.0

            if len(strategies) < 2:
                return 0.0
            
            # Count different indicators
            indicators = set()
            for strategy in strategies:
                indicator = strategy.get("signal_gene", {}).get("indicator")
                if indicator:
                    indicators.add(indicator)
            
            # Diversity: 0 if all same indicator, 1 if all different
            max_diversity = len(strategies)
            diversity = len(indicators) / max_diversity if max_diversity > 0 else 0
            
            logger.debug(
                "AlphaCompetition.measure_diversity: %d indicators from %d strategies",
                len(indicators), len(strategies)
            )
            
            return round(diversity, 4)
        
        except Exception as exc:
            logger.error("AlphaCompetition.measure_diversity failed: %s", exc)
            return 0.0
    
    # -----------------------------------------------------------------------
    # Private Helpers
    # -----------------------------------------------------------------------
    
    @staticmethod
    def _compare_strategies(
        s1: Dict[str, Any],
        s2: Dict[str, Any],
        metric: str = "fitness_score",
    ) -> Dict[str, Any]:
        """Compare two strategies, return winner."""
        m1 = s1.get("metrics", {}).get(metric, 0)
        m2 = s2.get("metrics", {}).get(metric, 0)
        
        # For drawdown, lower is better
        if metric == "max_drawdown":
            return s1 if m1 < m2 else s2
        else:
            return s1 if m1 > m2 else s2
    
    @staticmethod
    def _calculate_diversity(
        strategy: Dict[str, Any],
        reference_strategies: List[Dict[str, Any]],
    ) -> float:
        """Calculate how different this strategy is from a reference set."""
        try:
            if not reference_strategies:
                return 0.5
            
            # Extract characteristics
            indicator = strategy.get("signal_gene", {}).get("indicator")
            
            # Count how many have same indicator
            same_indicator = sum(
                1 for s in reference_strategies
                if s.get("signal_gene", {}).get("indicator") == indicator
            )
            
            # Diversity = 1 - (same / total)
            diversity = 1.0 - (same_indicator / len(reference_strategies))
            
            return diversity
        
        except Exception:
            return 0.5
    
    @staticmethod
    def _calculate_allocations(
        strategies: List[Dict[str, Any]],
        method: str = "equal_weight",
    ) -> List[float]:
        """Calculate capital allocation for portfolio."""
        try:
            n = len(strategies)
            
            if method == "equal_weight":
                return [1.0 / n] * n
            
            elif method == "fitness_weighted":
                fitnesses = [
                    s.get("metrics", {}).get("fitness_score", 1.0)
                    for s in strategies
                ]
                total = sum(fitnesses)
                return [f / total for f in fitnesses]
            
            elif method == "risk_parity":
                # Weight inversely by drawdown
                drawdowns = [
                    s.get("metrics", {}).get("max_drawdown", 0.1)
                    for s in strategies
                ]
                # Inverse weights
                weights = [1.0 / d for d in drawdowns]
                total = sum(weights)
                return [w / total for w in weights]
            
            else:
                # Default to equal
                return [1.0 / n] * n
        
        except Exception:
            return [1.0 / len(strategies)] * len(strategies)


class StrategySelector:
    """
    High-level strategy selector for the research loop.
    
    Selects strategies for backtesting, mutation, and live trading.
    """
    
    def __init__(self, bank: Any, competition: AlphaCompetition) -> None:
        self.bank = bank
        self.competition = competition
    
    def select_for_backtest(self, num: int = 20) -> List[Dict[str, Any]]:
        """Select strategies for backtesting (diverse set)."""
        return self.competition.select_for_breeding(num_parents=num)
    
    def select_for_mutation(self, num: int = 10) -> List[Dict[str, Any]]:
        """Select best strategies for mutation."""
        return self.bank.rank_strategies()[:num]
    
    def select_for_deployment(self, num: int = 5) -> List[Dict[str, Any]]:
        """Select best strategies for live trading."""
        elite = self.competition.select_elite()
        return elite[:num]
    
    def select_by_symbol(
        self,
        symbol: str,
        num: int = 10,
    ) -> List[Dict[str, Any]]:
        """Select best strategies for a specific symbol."""
        return self.bank.get_top_strategies(limit=num, symbol=symbol)

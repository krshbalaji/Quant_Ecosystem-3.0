"""
alpha_bank.py — Quant Ecosystem 3.0
====================================

Central strategy bank: store, rank, and manage discovered alpha strategies.

The AlphaBank serves as the memory system for the autonomous research loop.
It maintains:
  - All discovered strategy genomes
  - Performance metrics (Sharpe, Sortino, Calmar, etc.)
  - Fitness scores and rankings
  - Top N leaderboards (daily, weekly, monthly)
  - Strategy families and clusters

Usage:
    >>> bank = AlphaBank(storage_path="alpha_bank.db", mode="sqlite")
    >>> 
    >>> # Save a discovered strategy
    >>> strategy = {"genome_id": "...", "signal_gene": {...}, ...}
    >>> bank.save_strategy(strategy, symbol="NSE:INFY-EQ")
    >>> 
    >>> # Update performance after backtest
    >>> metrics = {"sharpe": 1.5, "drawdown": 0.15, "returns": 0.32, ...}
    >>> bank.update_performance("strategy_id", metrics)
    >>> 
    >>> # Get top performers
    >>> top_10 = bank.get_top_strategies(limit=10, metric="sharpe")
    >>> 
    >>> # Rank all strategies
    >>> rankings = bank.rank_strategies()
    >>> 
    >>> # Check fitness/viability
    >>> if bank.is_viable_strategy(strategy):
    ...     print("Strategy passed fitness checks")
    >>> 
    >>> # Get similar strategies for mutation
    >>> family = bank.get_strategy_family(strategy_id)
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class StrategyMetrics:
    """Performance metrics for a strategy."""
    
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    annual_return: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    num_trades: int = 0
    recovery_days: int = 0
    fitness_score: float = 0.0  # Composite score


class AlphaBank:
    """
    Central strategy bank for managing discovered alpha strategies.
    
    Features:
    - Store strategy genomes with full provenance
    - Track performance metrics across different market conditions
    - Rank strategies using multiple fitness metrics
    - Maintain leaderboards (daily, weekly, monthly)
    - Identify strategy families and clusters
    - Support both JSON and SQLite backends
    
    Parameters
    ----------
    storage_path : str, default="alpha_bank"
        Path for storage (directory for JSON, file for SQLite).
    mode : {"json", "sqlite"}, default="sqlite"
        Storage backend.
    max_strategies : int, default=100000
        Maximum strategies to keep (oldest removed).
    min_fitness : float, default=0.5
        Minimum fitness score for viability.
    cache_top_n : int, default=1000
        Cache top N strategies in memory for fast access.
    
    Examples
    --------
    >>> # Initialize
    >>> bank = AlphaBank(storage_path="alpha_bank.db", mode="sqlite")
    >>> 
    >>> # Save strategy
    >>> strategy = {
    ...     "genome_id": "arl_momentum_abc123",
    ...     "signal_gene": {
    ...         "indicator": "momentum",
    ...         "lookback": 20,
    ...         "threshold": 1.5,
    ...     },
    ...     "created_at": "2024-03-01T10:00:00Z",
    ... }
    >>> bank.save_strategy(strategy, symbol="NSE:INFY-EQ", source="discovery")
    >>> 
    >>> # Update metrics after backtest
    >>> metrics = StrategyMetrics(
    ...     sharpe_ratio=1.8,
    ...     sortino_ratio=2.1,
    ...     max_drawdown=0.12,
    ...     annual_return=0.42,
    ... )
    >>> bank.update_performance("arl_momentum_abc123", metrics)
    >>> 
    >>> # Get top strategies
    >>> top_20 = bank.get_top_strategies(limit=20)
    >>> for strategy in top_20:
    ...     print(f"{strategy['genome_id']}: Sharpe={strategy['metrics']['sharpe_ratio']:.2f}")
    >>> 
    >>> # Rank all strategies
    >>> rankings = bank.rank_strategies()
    >>> 
    >>> # Get strategy family (for mutation)
    >>> family = bank.get_strategy_family("arl_momentum_abc123", limit=10)
    """
    
    def __init__(
        self,
        storage_path: str = "alpha_bank",
        mode: str = "sqlite",
        max_strategies: int = 100000,
        min_fitness: float = 0.5,
        cache_top_n: int = 1000,
    ) -> None:
        self.storage_path = storage_path
        self.mode = mode.lower()
        self.max_strategies = max_strategies
        self.min_fitness = min_fitness
        self.cache_top_n = cache_top_n
        
        # In-memory caches
        self._cache_top_strategies: List[Dict[str, Any]] = []
        self._cache_timestamp = 0.0
        self._cache_ttl = 300  # 5 minutes
        self._lock = threading.RLock()
        
        # Statistics
        self._total_strategies = 0
        self._total_saved = 0
        
        # Initialize storage backend
        if self.mode == "sqlite":
            from .alpha_storage import SQLiteStorage
            self._storage = SQLiteStorage(storage_path)
        elif self.mode == "json":
            from .alpha_storage import JSONStorage
            self._storage = JSONStorage(storage_path)
        else:
            raise ValueError(f"Unknown storage mode: {mode}")
        
        self._storage.init()
        
        logger.info(
            "AlphaBank initialized (mode=%s, path=%s, max=%d)",
            self.mode, storage_path, max_strategies
        )
    
    # -----------------------------------------------------------------------
    # Strategy Management
    # -----------------------------------------------------------------------
    
    def save_strategy(
        self,
        strategy: Dict[str, Any],
        symbol: Optional[str] = None,
        source: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Save a discovered strategy genome.
        
        Parameters
        ----------
        strategy : dict
            Strategy genome with keys: genome_id, signal_gene, params, etc.
        symbol : str, optional
            Symbol this strategy was discovered on.
        source : str, default="unknown"
            Source of discovery (e.g., "discovery", "mutation", "crossover").
        metadata : dict, optional
            Additional metadata (researcher, parameters, notes, etc.).
        
        Returns
        -------
        str
            Strategy ID assigned by the bank.
        
        Examples
        --------
        >>> strategy = {
        ...     "genome_id": "arl_momentum_xyz789",
        ...     "signal_gene": {"indicator": "momentum", "lookback": 20},
        ... }
        >>> strategy_id = bank.save_strategy(
        ...     strategy,
        ...     symbol="BTCUSDT",
        ...     source="discovery"
        ... )
        """
        try:
            # Generate ID if not provided
            if "genome_id" not in strategy:
                strategy["genome_id"] = self._generate_genome_id()
            
            strategy_id = strategy.get("genome_id")

            if not isinstance(strategy_id, str):
                raise ValueError("strategy genome_id must be a non-empty string")
            
            # Add metadata
            if metadata is None:
                metadata = {}
            
            metadata.update({
                "symbol": symbol,
                "source": source,
                "created_at": datetime.now(tz=timezone.utc).isoformat(),
                "version": "1.0",
            })
            
            strategy["metadata"] = metadata
            
            # Save to storage
            self._storage.save_strategy(strategy_id, strategy)
            
            with self._lock:
                self._total_saved += 1
                self._total_strategies = max(
                    self._total_strategies,
                    self._storage.count_strategies()
                )
            
            logger.info(
                "AlphaBank.save_strategy: %s (symbol=%s, source=%s)",
                strategy_id, symbol, source
            )
            
            return strategy_id
        
        except Exception as exc:
            logger.error("AlphaBank.save_strategy failed: %s", exc)
            raise
    
    def update_performance(
        self,
        strategy_id: str,
        metrics: Dict[str, Any] | StrategyMetrics,
    ) -> None:
        """
        Update performance metrics for a strategy after backtest.
        
        Parameters
        ----------
        strategy_id : str
            Strategy ID to update.
        metrics : dict or StrategyMetrics
            Performance metrics with keys: sharpe_ratio, sortino_ratio,
            max_drawdown, annual_return, win_rate, etc.
        
        Examples
        --------
        >>> metrics = {
        ...     "sharpe_ratio": 1.8,
        ...     "sortino_ratio": 2.1,
        ...     "max_drawdown": 0.12,
        ...     "annual_return": 0.42,
        ...     "win_rate": 0.58,
        ...     "num_trades": 250,
        ... }
        >>> bank.update_performance("strategy_id", metrics)
        """
        try:
            # Retrieve strategy
            strategy = self._storage.get_strategy(strategy_id)
            if not strategy:
                logger.warning("Strategy not found: %s", strategy_id)
                return
            
            # Convert StrategyMetrics to dict if needed
            if isinstance(metrics, StrategyMetrics):
                metrics = asdict(metrics)
            
            # Calculate fitness score
            fitness = self._calculate_fitness(metrics)
            metrics["fitness_score"] = fitness
            
            # Update strategy
            strategy["metrics"] = metrics
            strategy["last_updated"] = datetime.now(tz=timezone.utc).isoformat()
            
            # Save back to storage
            self._storage.save_strategy(strategy_id, strategy)
            
            # Invalidate cache
            self._invalidate_cache()
            
            logger.info(
                "AlphaBank.update_performance: %s (fitness=%.3f)",
                strategy_id, fitness
            )
        
        except Exception as exc:
            logger.error("AlphaBank.update_performance failed: %s", exc)
            raise
    
    # -----------------------------------------------------------------------
    # Ranking and Retrieval
    # -----------------------------------------------------------------------
    
    def get_top_strategies(
        self,
        limit: int = 10,
        metric: str = "fitness_score",
        symbol: Optional[str] = None,
        min_trades: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get top-ranked strategies.
        
        Parameters
        ----------
        limit : int, default=10
            Number of strategies to return.
        metric : str, default="fitness_score"
            Ranking metric (sharpe_ratio, sortino_ratio, annual_return, etc.).
        symbol : str, optional
            Filter by symbol (if None, return all).
        min_trades : int, default=10
            Minimum number of trades (filter out strategies with insufficient data).
        
        Returns
        -------
        list
            Top strategies sorted by metric (descending).
        
        Examples
        --------
        >>> # Top 20 by Sharpe ratio
        >>> top_20 = bank.get_top_strategies(limit=20, metric="sharpe_ratio")
        >>> 
        >>> # Top 10 by annual return
        >>> best_returns = bank.get_top_strategies(
        ...     limit=10,
        ...     metric="annual_return"
        ... )
        >>> 
        >>> # Top strategies for specific symbol
        >>> btc_strategies = bank.get_top_strategies(
        ...     limit=5,
        ...     symbol="BTCUSDT"
        ... )
        """
        try:
            # Check cache
            if metric == "fitness_score" and symbol is None:
                with self._lock:
                    if self._cache_top_strategies and self._is_cache_valid():
                        return self._cache_top_strategies[:limit]
            
            # Get from storage
            strategies = self._storage.get_top_strategies(
                limit=limit,
                metric=metric,
                symbol=symbol,
                min_trades=min_trades,
            )
            
            # Cache if appropriate
            if metric == "fitness_score" and symbol is None:
                with self._lock:
                    self._cache_top_strategies = strategies[:self.cache_top_n]
                    self._cache_timestamp = datetime.now(tz=timezone.utc).timestamp()
            
            return strategies
        
        except Exception as exc:
            logger.error("AlphaBank.get_top_strategies failed: %s", exc)
            return []
    
    def rank_strategies(
        self,
        symbol: Optional[str] = None,
        min_fitness: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Rank all strategies by fitness score.
        
        Parameters
        ----------
        symbol : str, optional
            Filter by symbol.
        min_fitness : float, optional
            Minimum fitness threshold (default: self.min_fitness).
        
        Returns
        -------
        list
            All strategies ranked by fitness (descending).
        
        Examples
        --------
        >>> rankings = bank.rank_strategies()
        >>> print(f"Total strategies: {len(rankings)}")
        >>> 
        >>> # Filter by fitness
        >>> viable = bank.rank_strategies(min_fitness=1.0)
        >>> print(f"Viable strategies: {len(viable)}")
        """
        try:
            if min_fitness is None:
                min_fitness = self.min_fitness
            
            return self._storage.rank_strategies(
                symbol=symbol,
                min_fitness=min_fitness,
            )
        
        except Exception as exc:
            logger.error("AlphaBank.rank_strategies failed: %s", exc)
            return []
    
    def get_strategy(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific strategy by ID.
        
        Parameters
        ----------
        strategy_id : str
            Strategy ID.
        
        Returns
        -------
        dict or None
            Strategy record if found.
        """
        try:
            return self._storage.get_strategy(strategy_id)
        except Exception as exc:
            logger.error("AlphaBank.get_strategy failed: %s", exc)
            return None
    
    # -----------------------------------------------------------------------
    # Strategy Families and Clustering
    # -----------------------------------------------------------------------
    
    def get_strategy_family(
        self,
        strategy_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get similar strategies from the same family (for mutation).
        
        A strategy family consists of strategies with the same base indicator
        and similar parameters, useful for mutation-based evolution.
        
        Parameters
        ----------
        strategy_id : str
            Base strategy ID.
        limit : int, default=10
            Maximum similar strategies to return.
        
        Returns
        -------
        list
            Similar strategies ranked by fitness.
        
        Examples
        --------
        >>> # Get mutation candidates (similar strategies)
        >>> family = bank.get_strategy_family("base_strategy", limit=20)
        >>> for strategy in family:
        ...     print(f"Candidate: {strategy['genome_id']}")
        """
        try:
            strategy = self._storage.get_strategy(strategy_id)
            if not strategy:
                return []
            
            # Extract family characteristics
            indicator = self._get_indicator(strategy)
            symbol = strategy.get("metadata", {}).get("symbol")
            
            # Get similar strategies
            return self._storage.get_strategies_by_family(
                indicator=indicator,
                symbol=symbol,
                limit=limit,
                exclude=strategy_id,
            )
        
        except Exception as exc:
            logger.error("AlphaBank.get_strategy_family failed: %s", exc)
            return []
    
    def get_strategies_by_family(
        self,
        family_name: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get all strategies in a family (e.g., "momentum", "mean_reversion").
        
        Parameters
        ----------
        family_name : str
            Family name (indicator name).
        limit : int, default=100
            Maximum strategies to return.
        
        Returns
        -------
        list
            Strategies in the family, ranked by fitness.
        """
        try:
            return self._storage.get_strategies_by_family(
                indicator=family_name,
                limit=limit,
            )
        except Exception as exc:
            logger.error("AlphaBank.get_strategies_by_family failed: %s", exc)
            return []
    
    # -----------------------------------------------------------------------
    # Fitness and Viability
    # -----------------------------------------------------------------------
    
    def is_viable_strategy(self, strategy: Dict[str, Any]) -> bool:
        """
        Check if a strategy passes fitness criteria.
        
        Criteria:
        - Has performance metrics
        - Fitness score >= min_fitness
        - At least 10 trades
        - Positive Sharpe ratio
        - Reasonable drawdown (<50%)
        
        Parameters
        ----------
        strategy : dict
            Strategy record.
        
        Returns
        -------
        bool
            True if strategy is viable.
        """
        try:
            if "metrics" not in strategy:
                return False
            
            metrics = strategy["metrics"]
            
            # Check fitness
            if metrics.get("fitness_score", 0) < self.min_fitness:
                return False
            
            # Check trading activity
            if metrics.get("num_trades", 0) < 10:
                return False
            
            # Check Sharpe
            if metrics.get("sharpe_ratio", 0) <= 0:
                return False
            
            # Check drawdown
            if metrics.get("max_drawdown", 0) > 0.5:  # >50%
                return False
            
            return True
        
        except Exception as exc:
            logger.error("AlphaBank.is_viable_strategy failed: %s", exc)
            return False
    
    # -----------------------------------------------------------------------
    # Statistics and Reporting
    # -----------------------------------------------------------------------
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get bank statistics.
        
        Returns
        -------
        dict
            Statistics including total strategies, top performers, etc.
        """
        try:
            stats = {
                "total_strategies": self._storage.count_strategies(),
                "total_saved": self._total_saved,
                "mode": self.mode,
                "storage_path": self.storage_path,
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            }
            
            # Top strategies
            top_10 = self.get_top_strategies(limit=10)
            if top_10:
                stats["top_10"] = [
                    {
                        "genome_id": s["genome_id"],
                        "fitness": s.get("metrics", {}).get("fitness_score", 0),
                        "sharpe": s.get("metrics", {}).get("sharpe_ratio", 0),
                    }
                    for s in top_10
                ]
            
            return stats
        
        except Exception as exc:
            logger.error("AlphaBank.get_stats failed: %s", exc)
            return {}
    
    # -----------------------------------------------------------------------
    # Cleanup and Maintenance
    # -----------------------------------------------------------------------
    
    def cleanup(self, keep_top_n: int = 1000, min_fitness: float = 0.0) -> int:
        """
        Remove low-fitness strategies to manage storage.
        
        Parameters
        ----------
        keep_top_n : int, default=1000
            Keep top N strategies.
        min_fitness : float, default=0.0
            Remove strategies below this fitness.
        
        Returns
        -------
        int
            Number of strategies removed.
        """
        try:
            removed = self._storage.cleanup(
                keep_top_n=keep_top_n,
                min_fitness=min_fitness,
            )
            
            self._invalidate_cache()
            
            logger.info("AlphaBank.cleanup: removed %d strategies", removed)
            
            return removed
        
        except Exception as exc:
            logger.error("AlphaBank.cleanup failed: %s", exc)
            return 0
    
    def export_leaderboard(
        self,
        filepath: str,
        limit: int = 100,
        metric: str = "fitness_score",
    ) -> None:
        """
        Export top strategies to CSV/JSON file.
        
        Parameters
        ----------
        filepath : str
            Output file path (.csv or .json).
        limit : int, default=100
            Number of strategies to export.
        metric : str, default="fitness_score"
            Ranking metric.
        """
        try:
            strategies = self.get_top_strategies(limit=limit, metric=metric)
            
            if filepath.endswith(".csv"):
                self._export_csv(filepath, strategies)
            elif filepath.endswith(".json"):
                self._export_json(filepath, strategies)
            else:
                raise ValueError("Unsupported format (use .csv or .json)")
            
            logger.info("AlphaBank.export_leaderboard: exported %d strategies", len(strategies))
        
        except Exception as exc:
            logger.error("AlphaBank.export_leaderboard failed: %s", exc)
            raise
    
    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------
    
    def _calculate_fitness(self, metrics: Dict[str, float]) -> float:
        """
        Calculate composite fitness score from metrics.
        
        Fitness = 0.4*sharpe + 0.3*sortino + 0.2*annual_return + 0.1*win_rate
        Adjusted for drawdown (penalty)
        """
        try:
            sharpe = metrics.get("sharpe_ratio", 0)
            sortino = metrics.get("sortino_ratio", 0)
            returns = metrics.get("annual_return", 0)
            win_rate = metrics.get("win_rate", 0)
            drawdown = metrics.get("max_drawdown", 0)
            
            # Base fitness
            fitness = (
                0.4 * min(sharpe, 3.0) / 3.0 +  # Cap Sharpe at 3
                0.3 * min(sortino, 4.0) / 4.0 +  # Cap Sortino at 4
                0.2 * min(returns, 1.0) / 1.0 +  # Cap returns at 100%
                0.1 * min(win_rate, 1.0)         # Cap win rate at 100%
            )
            
            # Drawdown penalty
            if drawdown > 0:
                penalty = drawdown / 2.0  # 50% drawdown = -0.25 penalty
                fitness = max(0, fitness - penalty)
            
            return round(fitness, 4)
        
        except Exception:
            return 0.0
    
    @staticmethod
    def _get_indicator(strategy: Dict[str, Any]) -> Optional[str]:
        """Extract indicator name from strategy."""
        try:
            return strategy.get("signal_gene", {}).get("indicator")
        except Exception:
            return None
    
    @staticmethod
    def _generate_genome_id() -> str:
        """Generate unique genome ID."""
        import uuid
        return f"genome_{uuid.uuid4().hex[:12]}"
    
    def _is_cache_valid(self) -> bool:
        """Check if in-memory cache is fresh."""
        now = datetime.now(tz=timezone.utc).timestamp()
        return (now - self._cache_timestamp) < self._cache_ttl
    
    def _invalidate_cache(self) -> None:
        """Clear in-memory cache."""
        with self._lock:
            self._cache_top_strategies = []
            self._cache_timestamp = 0
    
    def _export_csv(self, filepath: str, strategies: List[Dict]) -> None:
        """Export strategies to CSV."""
        try:
            import csv
            
            with open(filepath, "w", newline="") as f:
                if not strategies:
                    return
                
                # Extract keys from first strategy
                keys = ["genome_id", "fitness_score", "sharpe_ratio", "sortino_ratio", "annual_return"]
                writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
                
                writer.writeheader()
                
                for strategy in strategies:
                    row = {"genome_id": strategy.get("genome_id")}
                    metrics = strategy.get("metrics", {})
                    row.update({k: metrics.get(k, "") for k in keys[1:]})
                    writer.writerow(row)
        
        except Exception as exc:
            logger.error("AlphaBank._export_csv failed: %s", exc)
            raise
    
    def _export_json(self, filepath: str, strategies: List[Dict]) -> None:
        """Export strategies to JSON."""
        try:
            import json
            
            with open(filepath, "w") as f:
                json.dump(strategies, f, indent=2)
        
        except Exception as exc:
            logger.error("AlphaBank._export_json failed: %s", exc)
            raise

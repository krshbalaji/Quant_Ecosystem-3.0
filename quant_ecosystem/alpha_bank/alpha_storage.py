"""
alpha_storage.py — Quant Ecosystem 3.0
=======================================

Storage backends for AlphaBank: JSON and SQLite.

Provides abstraction for persisting strategy data with different backends:
- JSONStorage: File-based storage using JSON
- SQLiteStorage: Database-backed storage using SQLite

Both backends implement the same interface for easy swapping.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """Abstract base for storage backends."""
    
    @abstractmethod
    def init(self) -> None:
        """Initialize storage (create tables/directories)."""
        pass
    
    @abstractmethod
    def save_strategy(self, strategy_id: str, strategy: Dict[str, Any]) -> None:
        """Save strategy record."""
        pass
    
    @abstractmethod
    def get_strategy(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve strategy by ID."""
        pass
    
    @abstractmethod
    def count_strategies(self) -> int:
        """Count total strategies."""
        pass
    
    @abstractmethod
    def get_top_strategies(
        self,
        limit: int = 10,
        metric: str = "fitness_score",
        symbol: Optional[str] = None,
        min_trades: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get top strategies by metric."""
        pass
    
    @abstractmethod
    def rank_strategies(
        self,
        symbol: Optional[str] = None,
        min_fitness: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Rank all strategies by fitness."""
        pass
    
    @abstractmethod
    def get_strategies_by_family(
        self,
        indicator: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 100,
        exclude: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get strategies by family (indicator)."""
        pass
    
    @abstractmethod
    def cleanup(self, keep_top_n: int = 1000, min_fitness: float = 0.0) -> int:
        """Remove low-fitness strategies."""
        pass


class JSONStorage(StorageBackend):
    """
    File-based JSON storage for strategies.
    
    Structure:
        storage_path/
        ├── strategies/
        │   ├── genome_id_1.json
        │   ├── genome_id_2.json
        │   └── ...
        └── index.json (metadata index)
    """
    
    def __init__(self, storage_path: str = "alpha_bank") -> None:
        self.storage_path = Path(storage_path)
        self.strategies_dir = self.storage_path / "strategies"
        self.index_path = self.storage_path / "index.json"
        self._lock = threading.RLock()
        self._index_cache: Dict[str, Dict[str, Any]] = {}
    
    def init(self) -> None:
        """Initialize directories."""
        try:
            self.storage_path.mkdir(parents=True, exist_ok=True)
            self.strategies_dir.mkdir(parents=True, exist_ok=True)
            
            # Initialize index if not exists
            if not self.index_path.exists():
                self._save_index({})
            else:
                self._load_index()
            
            logger.info("JSONStorage initialized at %s", self.storage_path)
        
        except Exception as exc:
            logger.error("JSONStorage.init failed: %s", exc)
            raise
    
    def save_strategy(self, strategy_id: str, strategy: Dict[str, Any]) -> None:
        """Save strategy to JSON file."""
        try:
            filepath = self.strategies_dir / f"{strategy_id}.json"
            
            # Save strategy file
            with open(filepath, "w") as f:
                json.dump(strategy, f, indent=2)
            
            # Update index
            with self._lock:
                index = self._load_index()
                index[strategy_id] = {
                    "saved_at": datetime.now(tz=timezone.utc).isoformat(),
                    "symbol": strategy.get("metadata", {}).get("symbol"),
                    "fitness": strategy.get("metrics", {}).get("fitness_score", 0),
                    "sharpe": strategy.get("metrics", {}).get("sharpe_ratio", 0),
                    "indicator": self._get_indicator(strategy),
                }
                self._save_index(index)
            
            logger.debug("JSONStorage.save_strategy: %s", strategy_id)
        
        except Exception as exc:
            logger.error("JSONStorage.save_strategy failed: %s", exc)
            raise
    
    def get_strategy(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve strategy from JSON file."""
        try:
            filepath = self.strategies_dir / f"{strategy_id}.json"
            
            if not filepath.exists():
                return None
            
            with open(filepath, "r") as f:
                return json.load(f)
        
        except Exception as exc:
            logger.error("JSONStorage.get_strategy failed: %s", exc)
            return None
    
    def count_strategies(self) -> int:
        """Count strategy files."""
        try:
            return len(list(self.strategies_dir.glob("*.json")))
        except Exception:
            return 0
    
    def get_top_strategies(
        self,
        limit: int = 10,
        metric: str = "fitness_score",
        symbol: Optional[str] = None,
        min_trades: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get top strategies from index."""
        try:
            with self._lock:
                index = self._load_index()
            
            # Filter by symbol
            if symbol:
                index = {k: v for k, v in index.items() if v.get("symbol") == symbol}
            
            # Filter by trades (load full strategy)
            strategies = []
            for strategy_id in sorted(index.keys(), key=lambda k: index[k].get(metric, 0), reverse=True):
                strategy = self.get_strategy(strategy_id)
                if strategy and strategy.get("metrics", {}).get("num_trades", 0) >= min_trades:
                    strategies.append(strategy)
                    if len(strategies) >= limit:
                        break
            
            return strategies
        
        except Exception as exc:
            logger.error("JSONStorage.get_top_strategies failed: %s", exc)
            return []
    
    def rank_strategies(
        self,
        symbol: Optional[str] = None,
        min_fitness: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Rank all strategies."""
        try:
            with self._lock:
                index = self._load_index()
            
            # Filter
            items = list(index.items())
            if symbol:
                items = [(k, v) for k, v in items if v.get("symbol") == symbol]
            if min_fitness > 0:
                items = [(k, v) for k, v in items if v.get("fitness", 0) >= min_fitness]
            
            # Sort by fitness
            items.sort(key=lambda x: x[1].get("fitness", 0), reverse=True)
            
            # Load full strategies
            strategies = []
            for strategy_id, _ in items:
                strategy = self.get_strategy(strategy_id)
                if strategy:
                    strategies.append(strategy)
            
            return strategies
        
        except Exception as exc:
            logger.error("JSONStorage.rank_strategies failed: %s", exc)
            return []
    
    def get_strategies_by_family(
        self,
        indicator: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 100,
        exclude: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get strategies by family."""
        try:
            with self._lock:
                index = self._load_index()
            
            # Filter
            items = list(index.items())
            if indicator:
                items = [(k, v) for k, v in items if v.get("indicator") == indicator]
            if symbol:
                items = [(k, v) for k, v in items if v.get("symbol") == symbol]
            if exclude:
                items = [(k, v) for k, v in items if k != exclude]
            
            # Sort by fitness
            items.sort(key=lambda x: x[1].get("fitness", 0), reverse=True)
            
            # Load full strategies
            strategies = []
            for strategy_id, _ in items[:limit]:
                strategy = self.get_strategy(strategy_id)
                if strategy:
                    strategies.append(strategy)
            
            return strategies
        
        except Exception as exc:
            logger.error("JSONStorage.get_strategies_by_family failed: %s", exc)
            return []
    
    def cleanup(self, keep_top_n: int = 1000, min_fitness: float = 0.0) -> int:
        """Remove low-fitness strategies."""
        try:
            with self._lock:
                index = self._load_index()
            
            # Identify strategies to keep
            items = list(index.items())
            items.sort(key=lambda x: x[1].get("fitness", 0), reverse=True)
            keep_ids = {k for k, _ in items[:keep_top_n]}
            
            # Filter by fitness
            items = [(k, v) for k, v in items if v.get("fitness", 0) >= min_fitness]
            keep_ids.update({k for k, _ in items})
            
            # Remove files not in keep set
            removed = 0
            for strategy_file in self.strategies_dir.glob("*.json"):
                strategy_id = strategy_file.stem
                if strategy_id not in keep_ids:
                    strategy_file.unlink()
                    removed += 1
            
            # Update index
            new_index = {k: v for k, v in index.items() if k in keep_ids}
            self._save_index(new_index)
            
            logger.info("JSONStorage.cleanup: removed %d strategies", removed)
            return removed
        
        except Exception as exc:
            logger.error("JSONStorage.cleanup failed: %s", exc)
            return 0
    
    def _load_index(self) -> Dict[str, Dict[str, Any]]:
        """Load index from file."""
        try:
            with open(self.index_path, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    
    def _save_index(self, index: Dict[str, Dict[str, Any]]) -> None:
        """Save index to file."""
        try:
            with open(self.index_path, "w") as f:
                json.dump(index, f, indent=2)
        except Exception as exc:
            logger.error("JSONStorage._save_index failed: %s", exc)
    
    @staticmethod
    def _get_indicator(strategy: Dict[str, Any]) -> Optional[str]:
        """Extract indicator from strategy."""
        try:
            return strategy.get("signal_gene", {}).get("indicator")
        except Exception:
            return None


class SQLiteStorage(StorageBackend):
    """
    Database-backed storage using SQLite.
    
    Schema:
    - strategies: genome_id, data, symbol, fitness, sharpe, indicator, etc.
    - performance_history: strategy_id, timestamp, sharpe, drawdown, etc. (future)
    """
    
    def __init__(self, db_path: str = "alpha_bank.db") -> None:
        self.db_path = db_path
        self._lock = threading.RLock()
        self._conn: Optional[sqlite3.Connection] = None
    
    def init(self) -> None:
        """Create database and tables."""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                # Strategies table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS strategies (
                        strategy_id TEXT PRIMARY KEY,
                        data TEXT NOT NULL,
                        symbol TEXT,
                        fitness REAL DEFAULT 0,
                        sharpe REAL DEFAULT 0,
                        sortino REAL DEFAULT 0,
                        annual_return REAL DEFAULT 0,
                        max_drawdown REAL DEFAULT 0,
                        win_rate REAL DEFAULT 0,
                        num_trades INTEGER DEFAULT 0,
                        indicator TEXT,
                        source TEXT,
                        created_at TEXT,
                        updated_at TEXT,
                        INDEX idx_fitness (fitness),
                        INDEX idx_symbol (symbol),
                        INDEX idx_indicator (indicator)
                    )
                """)
                
                # Performance history table (for future use)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS performance_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        strategy_id TEXT NOT NULL,
                        timestamp TEXT,
                        sharpe REAL,
                        sortino REAL,
                        annual_return REAL,
                        max_drawdown REAL,
                        FOREIGN KEY (strategy_id) REFERENCES strategies(strategy_id)
                    )
                """)
                
                conn.commit()
                logger.info("SQLiteStorage initialized at %s", db_path)
        
        except Exception as exc:
            logger.error("SQLiteStorage.init failed: %s", exc)
            raise
    
    def save_strategy(self, strategy_id: str, strategy: Dict[str, Any]) -> None:
        """Save strategy to database."""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                # Extract metrics
                metrics = strategy.get("metrics", {})
                metadata = strategy.get("metadata", {})
                
                # Insert or update
                cursor.execute("""
                    INSERT OR REPLACE INTO strategies (
                        strategy_id, data, symbol, fitness, sharpe, sortino,
                        annual_return, max_drawdown, win_rate, num_trades,
                        indicator, source, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    strategy_id,
                    json.dumps(strategy),
                    metadata.get("symbol"),
                    metrics.get("fitness_score", 0),
                    metrics.get("sharpe_ratio", 0),
                    metrics.get("sortino_ratio", 0),
                    metrics.get("annual_return", 0),
                    metrics.get("max_drawdown", 0),
                    metrics.get("win_rate", 0),
                    metrics.get("num_trades", 0),
                    strategy.get("signal_gene", {}).get("indicator"),
                    metadata.get("source"),
                    metadata.get("created_at"),
                    datetime.now(tz=timezone.utc).isoformat(),
                ))
                
                conn.commit()
                logger.debug("SQLiteStorage.save_strategy: %s", strategy_id)
        
        except Exception as exc:
            logger.error("SQLiteStorage.save_strategy failed: %s", exc)
            raise
    
    def get_strategy(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve strategy from database."""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute(
                    "SELECT data FROM strategies WHERE strategy_id = ?",
                    (strategy_id,)
                )
                
                row = cursor.fetchone()
                if row:
                    return json.loads(row[0])
            
            return None
        
        except Exception as exc:
            logger.error("SQLiteStorage.get_strategy failed: %s", exc)
            return None
    
    def count_strategies(self) -> int:
        """Count total strategies."""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM strategies")
                return cursor.fetchone()[0]
        
        except Exception:
            return 0
    
    def get_top_strategies(
        self,
        limit: int = 10,
        metric: str = "fitness",
        symbol: Optional[str] = None,
        min_trades: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get top strategies by metric."""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                # Map metric names
                metric_col = metric.replace("_score", "").replace("_ratio", "")
                
                query = f"""
                    SELECT data FROM strategies
                    WHERE num_trades >= ?
                """
                params = [min_trades]
                
                if symbol:
                    query += " AND symbol = ?"
                    params.append(symbol)
                
                query += f" ORDER BY {metric_col} DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(query, params)
                
                return [json.loads(row[0]) for row in cursor.fetchall()]
        
        except Exception as exc:
            logger.error("SQLiteStorage.get_top_strategies failed: %s", exc)
            return []
    
    def rank_strategies(
        self,
        symbol: Optional[str] = None,
        min_fitness: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Rank all strategies."""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                query = "SELECT data FROM strategies WHERE fitness >= ?"
                params = [min_fitness]
                
                if symbol:
                    query += " AND symbol = ?"
                    params.append(symbol)
                
                query += " ORDER BY fitness DESC"
                
                cursor.execute(query, params)
                
                return [json.loads(row[0]) for row in cursor.fetchall()]
        
        except Exception as exc:
            logger.error("SQLiteStorage.rank_strategies failed: %s", exc)
            return []
    
    def get_strategies_by_family(
        self,
        indicator: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 100,
        exclude: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get strategies by family."""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                query = "SELECT data FROM strategies WHERE 1=1"
                params = []
                
                if indicator:
                    query += " AND indicator = ?"
                    params.append(indicator)
                
                if symbol:
                    query += " AND symbol = ?"
                    params.append(symbol)
                
                if exclude:
                    query += " AND strategy_id != ?"
                    params.append(exclude)
                
                query += " ORDER BY fitness DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(query, params)
                
                return [json.loads(row[0]) for row in cursor.fetchall()]
        
        except Exception as exc:
            logger.error("SQLiteStorage.get_strategies_by_family failed: %s", exc)
            return []
    
    def cleanup(self, keep_top_n: int = 1000, min_fitness: float = 0.0) -> int:
        """Remove low-fitness strategies."""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                # Get IDs to keep
                cursor.execute("""
                    SELECT strategy_id FROM strategies
                    ORDER BY fitness DESC LIMIT ?
                """, (keep_top_n,))
                
                keep_ids = [row[0] for row in cursor.fetchall()]
                
                # Delete
                cursor.execute("""
                    DELETE FROM strategies
                    WHERE strategy_id NOT IN ({})
                    AND fitness < ?
                """.format(",".join("?" * len(keep_ids))),
                keep_ids + [min_fitness])
                
                removed = cursor.rowcount
                conn.commit()
                
                logger.info("SQLiteStorage.cleanup: removed %d strategies", removed)
                return removed
        
        except Exception as exc:
            logger.error("SQLiteStorage.cleanup failed: %s", exc)
            return 0
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        return self._conn

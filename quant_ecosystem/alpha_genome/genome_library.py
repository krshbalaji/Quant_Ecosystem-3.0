"""Genome Library — persistent in-memory store for alpha genomes.

Provides thread-safe storage, retrieval, and enumeration of genome dicts
produced by the alpha-genome pipeline. No external dependencies required.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class AlphaGenomeLibrary:
    """
    Stores discovered alpha genomes.
    """

    def __init__(self):
        self.genomes = {}

    def store(self, name, genome):
        self.genomes[name] = genome

    def get(self, name):
        return self.genomes.get(name)

    def list(self):
        return list(self.genomes.keys())

class GenomeLibrary:
    """Central registry for alpha genomes.

    Stores genomes keyed by a unique genome_id. All operations are
    thread-safe so the library can be shared across async workers and
    the main trading loop without external locking.

    Usage
    -----
    >>> lib = GenomeLibrary()
    >>> lib.store_genome("g1", {"params": {"rsi_period": 14}, "score": 0.72})
    >>> lib.get_genome("g1")
    {'params': {'rsi_period': 14}, 'score': 0.72}
    >>> lib.list_genomes()
    ['g1']
    """

    def __init__(
        self,
        max_capacity: int = 10_000,
    ) -> None:
        self.max_capacity = max(1, int(max_capacity))
        self._store: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        logger.info(
            "GenomeLibrary initialized (capacity=%d)", self.max_capacity
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def store_genome(
        self,
        genome_id: str,
        genome: Dict[str, Any],
        *,
        overwrite: bool = True,
    ) -> bool:
        """Persist *genome* under *genome_id*.

        Parameters
        ----------
        genome_id:
            Unique string identifier (e.g. ``"alpha_momentum_v3"``).
        genome:
            Arbitrary dict representing genome parameters, scores, etc.
        overwrite:
            When ``False`` the call is a no-op if the id already exists
            and returns ``False``.

        Returns
        -------
        bool
            ``True`` if the genome was stored, ``False`` otherwise.
        """
        if not genome_id:
            logger.warning("GenomeLibrary.store_genome: empty genome_id — skipped")
            return False

        with self._lock:
            if not overwrite and genome_id in self._store:
                logger.debug("GenomeLibrary.store_genome: %s already exists, skip", genome_id)
                return False

            if len(self._store) >= self.max_capacity and genome_id not in self._store:
                logger.warning(
                    "GenomeLibrary at capacity (%d). Evicting oldest entry.", self.max_capacity
                )
                try:
                    oldest = next(iter(self._store))
                    del self._store[oldest]
                except StopIteration:
                    pass

            self._store[genome_id] = dict(genome)
            logger.debug("GenomeLibrary.store_genome: stored %s", genome_id)
            return True

    def get_genome(self, genome_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a genome by id.

        Returns ``None`` when the id is not found (never raises).
        """
        with self._lock:
            result = self._store.get(genome_id)
        if result is None:
            logger.debug("GenomeLibrary.get_genome: %s not found", genome_id)
        return dict(result) if result is not None else None

    def list_genomes(self, *, prefix: str = "") -> List[str]:
        """Return all stored genome ids, optionally filtered by *prefix*.

        Parameters
        ----------
        prefix:
            Only ids starting with this string are returned. Pass ``""``
            (default) to list all.
        """
        with self._lock:
            ids = list(self._store.keys())
        if prefix:
            ids = [gid for gid in ids if gid.startswith(prefix)]
        return ids

    def delete_genome(self, genome_id: str) -> bool:
        """Remove a genome from the library.

        Returns ``True`` if it existed and was removed, ``False`` if not found.
        """
        with self._lock:
            existed = genome_id in self._store
            if existed:
                del self._store[genome_id]
                logger.debug("GenomeLibrary.delete_genome: removed %s", genome_id)
        return existed

    def clear(self) -> int:
        """Remove all genomes. Returns the number of entries deleted."""
        with self._lock:
            count = len(self._store)
            self._store.clear()
        logger.info("GenomeLibrary.clear: removed %d genomes", count)
        return count

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)

    def __repr__(self) -> str:
        return f"GenomeLibrary(count={len(self)}, capacity={self.max_capacity})"

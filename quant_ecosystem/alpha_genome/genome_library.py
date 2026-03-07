"""
quant_ecosystem/alpha_genome/genome_library.py
===============================================
Genome Library — Quant Ecosystem 3.0

Enhanced with:
• GenomeRecord dataclass — carries genome_id, parent_ids, mutation_type,
  generation, fitness_score, creation_timestamp alongside the raw genome dict.
• GenomeLibrary.store_record() — preferred write path that accepts GenomeRecord.
• GenomeLibrary.store_genome() — fully backward-compatible; auto-promotes to
  GenomeRecord internally.
• GenomeLibrary.update_fitness() — post-evaluation fitness write-back.
• GenomeLibrary.top_genomes()  — ranked read path used by StrategyLab.
• GenomeLibrary.get_record()   — returns GenomeRecord (not just raw dict).
• Optional ResearchMemoryLayer bridge — called on every store/update.

All existing callers of store_genome() / get_genome() / list_genomes() /
delete_genome() continue to work without modification.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_NOW = lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ---------------------------------------------------------------------------
# GenomeRecord
# ---------------------------------------------------------------------------

@dataclass
class GenomeRecord:
    """
    Enriched wrapper around a raw genome dict.

    Fields
    ------
    genome_id           Unique identifier (mirrors genome["genome_id"])
    genome              Full raw genome dict (genes + metadata)
    parent_ids          [] seed | [pid] mutation | [pid,pid] crossover
    mutation_type       "seed" | "mutation" | "crossover"
    generation          Evolution depth (0 = seed)
    fitness_score       Latest composite fitness
    sharpe              Latest Sharpe ratio
    drawdown            Latest max drawdown (negative)
    profit_factor       Latest profit factor
    win_rate            Latest win rate (0-100)
    trade_count         Trades in latest evaluation
    status              "discovered" | "shadow" | "live" | "retired"
    creation_timestamp  ISO-8601 UTC
    updated_at          ISO-8601 UTC of last write
    tags                Free-form labels
    """

    genome_id:           str
    genome:              Dict[str, Any]   = field(default_factory=dict)
    parent_ids:          List[str]        = field(default_factory=list)
    mutation_type:       str              = "seed"
    generation:         int              = 0
    fitness_score:       float            = 0.0
    sharpe:              float            = 0.0
    drawdown:            float            = 0.0
    profit_factor:       float            = 0.0
    win_rate:            float            = 0.0
    trade_count:         int              = 0
    status:              str              = "discovered"
    family:              str              = "unknown"
    creation_timestamp:  str              = field(default_factory=_NOW)
    updated_at:          str              = field(default_factory=_NOW)
    tags:                List[str]        = field(default_factory=list)

    def is_seed(self) -> bool:
        return not self.parent_ids

    def primary_parent_id(self) -> Optional[str]:
        return self.parent_ids[0] if self.parent_ids else None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_genome_dict(
        cls,
        genome:        Dict[str, Any],
        parent_ids:    Optional[List[str]] = None,
        mutation_type: str                 = "seed",
        generation:    int                 = 0,
        tags:          Optional[List[str]] = None,
    ) -> "GenomeRecord":
        """Create a GenomeRecord from a raw genome dict, auto-detecting lineage."""
        gid = str(genome.get("genome_id", f"genome_{int(time.time())}"))
        if parent_ids is None:
            meta       = genome.get("metadata") or {}
            crossbred  = meta.get("crossbred_from")
            origin     = meta.get("mutation_origin")
            if crossbred and isinstance(crossbred, list):
                parent_ids    = [str(p) for p in crossbred[:2]]
                mutation_type = "crossover"
            elif origin:
                parent_ids    = [str(origin)]
                mutation_type = "mutation"
            else:
                parent_ids    = []
                mutation_type = "seed"
        meta = genome.get("metadata") or {}
        gen  = generation or int(meta.get("generation", 0))
        return cls(
            genome_id     = gid,
            genome        = genome,
            parent_ids    = parent_ids or [],
            mutation_type = mutation_type,
            generation    = gen,
            tags          = tags or ["genome"],
        )


# ---------------------------------------------------------------------------
# AlphaGenomeLibrary — legacy simple store
# ---------------------------------------------------------------------------

class AlphaGenomeLibrary:
    """Simple store kept for backward compatibility with existing callers."""

    def __init__(self, **kwargs):
        self.genomes = {}

    def store(self, name: str, genome: Dict) -> None:
        self.genomes[name] = genome

    def get(self, name: str) -> Optional[Dict]:
        return self.genomes.get(name)

    def list(self) -> List[str]:
        return list(self.genomes.keys())


# ---------------------------------------------------------------------------
# GenomeLibrary — enhanced registry
# ---------------------------------------------------------------------------

class GenomeLibrary:
    """
    Central registry for alpha genomes.

    Backward-compatible API
    -----------------------
    store_genome(genome_id, genome_dict)   bool
    get_genome(genome_id)                  dict | None
    list_genomes(prefix="")               List[str]
    delete_genome(genome_id)              bool
    clear()                                int
    len()                                  int

    New API
    -------
    store_record(record)                   bool
    get_record(genome_id)                  GenomeRecord | None
    update_fitness(genome_id, metrics...)  bool
    top_genomes(n, status)                 List[GenomeRecord]
    summary()                              dict
    set_research_memory(rm)                None  (late wire)
    """

    def __init__(self, max_capacity: int = 10_000, research_memory=None, **kwargs) -> None:
        self.max_capacity = max(1, int(max_capacity))
        self._store: Dict[str, GenomeRecord] = {}
        self._lock  = threading.Lock()
        self._bridge = None
        if research_memory is not None:
            self._wire_bridge(research_memory)
        logger.info("GenomeLibrary initialized (capacity=%d, memory_bridge=%s)",
                    self.max_capacity, "active" if self._bridge else "inactive")

    def set_research_memory(self, research_memory) -> None:
        """Late-wire the ResearchMemoryLayer after construction."""
        self._wire_bridge(research_memory)

    def _wire_bridge(self, rm) -> None:
        try:
            from quant_ecosystem.alpha_genome._memory_bridge import GenomeMemoryBridge
            self._bridge = GenomeMemoryBridge(research_memory=rm)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Write — GenomeRecord (preferred)
    # ------------------------------------------------------------------

    def store_record(self, record: GenomeRecord, *, overwrite: bool = True) -> bool:
        gid = record.genome_id
        if not gid:
            logger.warning("GenomeLibrary.store_record: empty genome_id — skipped")
            return False
        with self._lock:
            if not overwrite and gid in self._store:
                return False
            self._evict_if_full(gid)
            record.updated_at = _NOW()
            self._store[gid]  = record
        if self._bridge:
            self._bridge.record_library_store(
                genome_id=gid, genome=record.genome,
                generation=record.generation, fitness_score=record.fitness_score,
            )
        logger.debug("GenomeLibrary.store_record: %s gen=%d type=%s",
                     gid, record.generation, record.mutation_type)
        return True

    # ------------------------------------------------------------------
    # Write — raw dict (backward compat)
    # ------------------------------------------------------------------

    def store_genome(self, genome_id: str, genome: Dict[str, Any], *, overwrite: bool = True) -> bool:
        if not genome_id:
            logger.warning("GenomeLibrary.store_genome: empty genome_id — skipped")
            return False
        rec = GenomeRecord.from_genome_dict(genome)
        rec.genome_id = genome_id
        rec.genome["genome_id"] = genome_id
        return self.store_record(rec, overwrite=overwrite)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_genome(self, genome_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            rec = self._store.get(genome_id)
        if rec is None:
            logger.debug("GenomeLibrary.get_genome: %s not found", genome_id)
            return None
        return dict(rec.genome)

    def get_record(self, genome_id: str) -> Optional[GenomeRecord]:
        with self._lock:
            return self._store.get(genome_id)

    def list_genomes(self, *, prefix: str = "") -> List[str]:
        with self._lock:
            ids = list(self._store.keys())
        if prefix:
            ids = [i for i in ids if i.startswith(prefix)]
        return ids

    def top_genomes(self, n: int = 20, status: Optional[str] = None) -> List[GenomeRecord]:
        with self._lock:
            records = list(self._store.values())
        if status:
            records = [r for r in records if r.status == status]
        records.sort(key=lambda r: r.fitness_score, reverse=True)
        return records[:n]

    # ------------------------------------------------------------------
    # Fitness write-back
    # ------------------------------------------------------------------

    def update_fitness(
        self,
        genome_id:     str,
        fitness_score: float,
        sharpe:        float = 0.0,
        drawdown:      float = 0.0,
        profit_factor: float = 0.0,
        win_rate:      float = 0.0,
        trade_count:   int   = 0,
    ) -> bool:
        with self._lock:
            rec = self._store.get(genome_id)
            if rec is None:
                return False
            rec.fitness_score = fitness_score
            rec.sharpe        = sharpe
            rec.drawdown      = drawdown
            rec.profit_factor = profit_factor
            rec.win_rate      = win_rate
            rec.trade_count   = trade_count
            rec.updated_at    = _NOW()
            rec.genome.setdefault("metadata", {})["fitness_score"] = fitness_score
            rec.genome["fitness_score"] = fitness_score
        return True

    # ------------------------------------------------------------------
    # Delete / clear
    # ------------------------------------------------------------------

    def delete_genome(self, genome_id: str) -> bool:
        with self._lock:
            existed = genome_id in self._store
            if existed:
                del self._store[genome_id]
                logger.debug("GenomeLibrary.delete_genome: removed %s", genome_id)
        return existed

    def clear(self) -> int:
        with self._lock:
            count = len(self._store)
            self._store.clear()
        logger.info("GenomeLibrary.clear: removed %d genomes", count)
        return count

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            records = list(self._store.values())
        if not records:
            return {"total": 0}
        scored = [r for r in records if r.fitness_score > 0]
        return {
            "total":          len(records),
            "evaluated":      len(scored),
            "seeds":          sum(1 for r in records if r.is_seed()),
            "avg_fitness":    round(sum(r.fitness_score for r in scored) / len(scored), 6) if scored else 0.0,
            "best_fitness":   round(max(r.fitness_score for r in scored), 6) if scored else 0.0,
            "best_genome_id": max(records, key=lambda r: r.fitness_score).genome_id if records else "",
            "capacity_used":  f"{len(records)}/{self.max_capacity}",
        }

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)

    def __repr__(self) -> str:
        return f"GenomeLibrary(count={len(self)}, capacity={self.max_capacity})"

    def _evict_if_full(self, incoming_id: str) -> None:
        if len(self._store) >= self.max_capacity and incoming_id not in self._store:
            logger.warning("GenomeLibrary at capacity (%d). Evicting lowest-fitness entry.", self.max_capacity)
            try:
                worst = min(self._store.values(), key=lambda r: r.fitness_score)
                del self._store[worst.genome_id]
            except (ValueError, KeyError):
                pass

"""
quant_ecosystem/alpha_genome/genome_snapshot.py
================================================
Genome Snapshot Scheduler — Quant Ecosystem 3.0

Provides:
• GenomeSnapshotScheduler — background thread that fires a ResearchMemoryLayer
  snapshot every N seconds (default: once per 24 hours post-market).
• genome_snapshot()        — one-shot convenience function.
• GenomeSnapshotContext    — context manager for wrapping a genome cycle.

Integration
-----------
The scheduler is wired into SystemFactory or called manually from the
autonomous controller's post-market maintenance routine:

    # In AutonomousController.run_nightly_maintenance():
    from quant_ecosystem.alpha_genome.genome_snapshot import genome_snapshot
    genome_snapshot(
        research_memory = router.research_memory,
        genome_library  = router.genome_library,
        label           = "eod_genome_cycle",
        quant_mode      = router.mode,
    )

Or with the scheduler (starts a daemon thread):

    scheduler = GenomeSnapshotScheduler(
        research_memory = router.research_memory,
        genome_library  = router.genome_library,
        interval_sec    = 86400,   # 24 hours
    )
    scheduler.start()
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# One-shot snapshot function
# ---------------------------------------------------------------------------

def genome_snapshot(
    research_memory  = None,
    genome_library   = None,
    label:      str  = "",
    notes:      str  = "",
    quant_mode: str  = "PAPER",
    trigger:    str  = "scheduled",
) -> Optional[Any]:
    """
    Create a full ResearchMemoryLayer snapshot enriched with genome library stats.

    Parameters
    ----------
    research_memory   ResearchMemoryLayer instance (router.research_memory)
    genome_library    GenomeLibrary instance (optional — adds genome stats to notes)
    label             Human-readable snapshot label, e.g. "eod_genome_cycle"
    notes             Free-text annotation
    quant_mode        "PAPER" | "LIVE"
    trigger           "scheduled" | "manual" | "event"

    Returns
    -------
    ResearchSnapshot on success, None if research_memory is not available.
    """
    if research_memory is None:
        logger.debug("[genome_snapshot] research_memory not available — skipping")
        return None

    # Enrich notes with genome library stats
    enriched_notes = notes
    if genome_library is not None:
        try:
            summary = genome_library.summary()
            enriched_notes = (
                f"{notes} | genome_library: total={summary.get('total', 0)} "
                f"evaluated={summary.get('evaluated', 0)} "
                f"best_fitness={summary.get('best_fitness', 0):.6f}"
            ).strip(" |")
        except Exception:
            pass

    auto_label = label or f"genome_cycle_{time.strftime('%Y_%m_%d_%H%M')}"

    try:
        snap = research_memory.snapshots.create(
            alpha_store  = research_memory._alpha_store,
            genealogy    = research_memory._genealogy,
            perf_archive = research_memory._perf,
            tracker      = research_memory._tracker,
            label        = auto_label,
            trigger      = trigger,
            notes        = enriched_notes,
            quant_mode   = quant_mode,
        )
        logger.info(
            "[genome_snapshot] snapshot created: %s  alphas=%d  label=%s",
            snap.manifest.snapshot_id,
            snap.manifest.alpha_count,
            snap.manifest.label,
        )
        return snap
    except Exception as exc:
        logger.warning("[genome_snapshot] failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Context manager — wraps one genome evolution cycle
# ---------------------------------------------------------------------------

class GenomeSnapshotContext:
    """
    Context manager that automatically snapshots before and after a genome cycle.

    Usage::

        with GenomeSnapshotContext(research_memory, genome_library, label="cycle_42") as ctx:
            new_genomes = generator.generate_random(50)
            mutants     = generator.generate_from_mutation(elites, variants_per_base=5)
            reports     = evaluator.evaluate_genomes(new_genomes + mutants)
            ctx.record_cycle_stats(total_evaluated=len(reports),
                                   best_fitness=max(r["fitness_score"] for r in reports))
        # Post-cycle snapshot taken automatically on __exit__
    """

    def __init__(
        self,
        research_memory = None,
        genome_library  = None,
        label:     str  = "",
        quant_mode: str = "PAPER",
    ) -> None:
        self._rm          = research_memory
        self._lib         = genome_library
        self._label       = label
        self._quant_mode  = quant_mode
        self._cycle_stats: Dict[str, Any] = {}
        self._start_time: float = 0.0

    def record_cycle_stats(self, **kwargs) -> None:
        """Store arbitrary cycle statistics that will be included in snapshot notes."""
        self._cycle_stats.update(kwargs)

    def __enter__(self) -> "GenomeSnapshotContext":
        self._start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, _tb) -> bool:
        duration = round(time.time() - self._start_time, 2)
        stats_str = " ".join(f"{k}={v}" for k, v in self._cycle_stats.items())
        status    = "ok" if exc_type is None else f"error:{exc_val}"
        notes     = f"duration={duration}s status={status} {stats_str}".strip()
        genome_snapshot(
            research_memory = self._rm,
            genome_library  = self._lib,
            label           = self._label or f"genome_cycle_{time.strftime('%Y_%m_%d_%H%M')}",
            notes           = notes,
            quant_mode      = self._quant_mode,
            trigger         = "event",
        )
        return False    # do not suppress exceptions


# ---------------------------------------------------------------------------
# Background scheduler
# ---------------------------------------------------------------------------

class GenomeSnapshotScheduler:
    """
    Background daemon thread that creates periodic genome snapshots.

    Usage::

        scheduler = GenomeSnapshotScheduler(
            research_memory = router.research_memory,
            genome_library  = router.genome_library,
            interval_sec    = 86400,   # 24 hours
            quant_mode      = "PAPER",
        )
        scheduler.start()

        # On shutdown:
        scheduler.stop()
    """

    def __init__(
        self,
        research_memory  = None,
        genome_library   = None,
        interval_sec:    float = 86_400.0,   # default: nightly
        quant_mode:      str   = "PAPER",
        run_immediately: bool  = False,
    ) -> None:
        self._rm          = research_memory
        self._lib         = genome_library
        self._interval    = max(60.0, float(interval_sec))
        self._quant_mode  = quant_mode
        self._run_now     = run_immediately
        self._stop_event  = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._snapshot_count = 0

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target  = self._run,
            name    = "GenomeSnapshotScheduler",
            daemon  = True,
        )
        self._thread.start()
        logger.info(
            "[GenomeSnapshotScheduler] started — interval=%.0fs quant_mode=%s",
            self._interval, self._quant_mode,
        )

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("[GenomeSnapshotScheduler] stopped after %d snapshots", self._snapshot_count)

    def trigger_now(self, label: str = "") -> Optional[Any]:
        """Manually trigger an immediate snapshot from outside the scheduler."""
        return genome_snapshot(
            research_memory = self._rm,
            genome_library  = self._lib,
            label           = label or "manual_trigger",
            quant_mode      = self._quant_mode,
            trigger         = "manual",
        )

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def snapshot_count(self) -> int:
        return self._snapshot_count

    # ------------------------------------------------------------------
    # Internal loop
    # ------------------------------------------------------------------

    def _run(self) -> None:
        if self._run_now:
            self._fire_snapshot("startup_snapshot")

        while not self._stop_event.wait(timeout=self._interval):
            self._fire_snapshot(f"scheduled_{time.strftime('%Y_%m_%d_%H%M')}")

    def _fire_snapshot(self, label: str) -> None:
        try:
            result = genome_snapshot(
                research_memory = self._rm,
                genome_library  = self._lib,
                label           = label,
                quant_mode      = self._quant_mode,
                trigger         = "scheduled",
            )
            if result:
                self._snapshot_count += 1
        except Exception as exc:
            logger.warning("[GenomeSnapshotScheduler] snapshot error: %s", exc)

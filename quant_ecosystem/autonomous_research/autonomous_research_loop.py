"""
quant_ecosystem/autonomous_research/autonomous_research_loop.py
===============================================================
Autonomous Research Loop — Quant Ecosystem 3.0

Runs a continuous hedge-fund research laboratory in a background daemon thread.
Every N seconds it executes the full research cycle:

    DISCOVER -> MUTATE -> EVOLVE -> SUBMIT -> EVALUATE -> RANK -> PROMOTE -> LEARN

Architecture
------------

                    +-------------------------------------------------+
                    |           AutonomousResearchLoop                |
                    |            (background daemon thread)           |
                    +-------------------------------------------------+
                                       |  each cycle
              +------------------------+--------------------------------+
              |                        |                               |
      +-------+------+        +--------+-------+            +----------+------+
      |  Discovery   |        |  Mutation /    |            |  Evolution      |
      |  Phase       |        |  Crossbreed    |            |  Phase          |
      |              |        |  Phase         |            |                 |
      | SDE.discover |        | SME.mutate     |            | AEE.evolve      |
      +-------+------+        +--------+-------+            +----------+------+
              |                        |                               |
              +------------------------+-------------------------------+
                                       |  merged genome batch
                               +-------+---------+
                               |  Evaluation     |
                               |  Phase          |
                               |                 |
                               | ResearchGrid    |
                               |  .run_cycle()   |
                               +-------+---------+
                                       |  ranked results
                               +-------+---------+
                               |  Promotion      |
                               |  Phase          |
                               |                 |
                               | GenomeLibrary   |
                               | StrategyBank    |
                               +-------+---------+
                                       |
                               +-------+---------+
                               |  Learning       |
                               |  Phase          |
                               |                 |
                               | MetaResearchAI  |
                               |  .refresh()     |
                               +-----------------+

Thread safety
-------------
All shared state is guarded by threading.Lock().  The loop thread never
touches market execution -- it is strictly read/write on research objects.

Component injection
-------------------
All components are optional at construction time.  Any absent component
is gracefully skipped with a WARNING, allowing the loop to run with
whatever subset of engines is available.

Configuration
-------------
Passed via LoopConfig dataclass.  Key settings:

    cycle_interval_sec      seconds between cycle starts   (default 120)
    discovery_batch_size    genomes to discover per cycle  (default 30)
    mutation_batch_size     mutations per top-genome       (default 15)
    evolution_top_n         top library genomes fed to AEE (default 10)
    eval_symbols            symbols to backtest against    (default SYNTH)
    eval_periods            backtest candle count          (default 260)
    promote_threshold       min fitness for promotion      (default 0.45)
    promote_top_n           hard cap on promoted genomes   (default 5)
    enable_walk_forward     run walk-forward on top-N      (default True)
    enable_monte_carlo      run Monte Carlo on top-5       (default False)

Cycle state
-----------
CycleState captures a full audit trail: timestamps, genome counts, fitness
stats, promotion count, errors.  Accessible via loop.last_cycle and
loop.cycle_history (ring buffer, last 100).

Public API
----------
    start()             launch daemon thread (idempotent)
    stop()              signal thread to stop, wait for clean exit
    trigger_now()       signal an immediate extra cycle (non-blocking)
    status()            dict snapshot of current loop health
    last_cycle          most recent CycleState (or None)
    cycle_history       list of last N CycleStates
    is_running          bool property
"""

from __future__ import annotations

import copy
import logging
import random
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)

_LOG_TAG = "[research_loop]"


# ---------------------------------------------------------------------------
# LoopConfig
# ---------------------------------------------------------------------------

@dataclass
class LoopConfig:
    """Tunable parameters for the AutonomousResearchLoop."""

    # Timing
    cycle_interval_sec:    float = 120.0
    eval_timeout_sec:      float = 90.0
    startup_delay_sec:     float = 5.0

    # Batch sizes
    discovery_batch_size:  int   = 30
    mutation_batch_size:   int   = 15
    evolution_top_n:       int   = 10
    random_injection:      int   = 5

    # Evaluation
    eval_symbols:          List[str] = field(default_factory=lambda: ["SYNTH"])
    eval_periods:          int   = 260

    # Promotion
    promote_threshold:     float = 0.45
    promote_top_n:         int   = 5

    # Advanced evaluation stages
    enable_walk_forward:   bool  = True
    enable_monte_carlo:    bool  = False
    walk_forward_n:        int   = 5
    monte_carlo_runs:      int   = 100

    # Safety
    max_concurrent_cycles: int   = 1
    max_genome_batch:      int   = 200

    # Logging / history
    log_prefix:            str   = _LOG_TAG
    history_size:          int   = 100

    def __post_init__(self) -> None:
        self.cycle_interval_sec    = max(10.0,  float(self.cycle_interval_sec))
        self.eval_timeout_sec      = max(10.0,  float(self.eval_timeout_sec))
        self.startup_delay_sec     = max(0.0,   float(self.startup_delay_sec))
        self.discovery_batch_size  = max(1,     int(self.discovery_batch_size))
        self.mutation_batch_size   = max(0,     int(self.mutation_batch_size))
        self.evolution_top_n       = max(0,     int(self.evolution_top_n))
        self.random_injection      = max(0,     int(self.random_injection))
        self.eval_periods          = max(50,    int(self.eval_periods))
        self.promote_threshold     = max(0.0, min(1.0, float(self.promote_threshold)))
        self.promote_top_n         = max(1,     int(self.promote_top_n))
        self.max_concurrent_cycles = max(1,     int(self.max_concurrent_cycles))
        self.max_genome_batch      = max(10,    int(self.max_genome_batch))
        self.history_size          = max(10,    int(self.history_size))
        if not self.eval_symbols:
            self.eval_symbols = ["SYNTH"]


# ---------------------------------------------------------------------------
# CycleState
# ---------------------------------------------------------------------------

@dataclass
class CycleState:
    """Full audit record for a single research cycle."""

    cycle_id:           str   = ""
    cycle_number:       int   = 0
    started_at:         float = 0.0
    finished_at:        float = 0.0
    elapsed_sec:        float = 0.0

    # Phase outcomes
    discovered_count:   int   = 0
    mutated_count:      int   = 0
    evolved_count:      int   = 0
    random_count:       int   = 0
    submitted_count:    int   = 0
    evaluated_count:    int   = 0
    promoted_count:     int   = 0

    # Quality metrics
    best_fitness:       float = 0.0
    avg_fitness:        float = 0.0
    best_sharpe:        float = 0.0
    best_genome_id:     str   = ""
    top_genomes:        List[Dict] = field(default_factory=list)

    # Audit
    errors:             List[str] = field(default_factory=list)
    phases_completed:   List[str] = field(default_factory=list)
    phases_skipped:     List[str] = field(default_factory=list)
    ok:                 bool  = False

    def mark_started(self) -> None:
        self.started_at = time.time()

    def mark_finished(self) -> None:
        self.finished_at = time.time()
        self.elapsed_sec = round(self.finished_at - self.started_at, 3)
        self.ok = len(self.errors) == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycle_id":         self.cycle_id,
            "cycle_number":     self.cycle_number,
            "started_at":       self.started_at,
            "finished_at":      self.finished_at,
            "elapsed_sec":      self.elapsed_sec,
            "discovered":       self.discovered_count,
            "mutated":          self.mutated_count,
            "evolved":          self.evolved_count,
            "random":           self.random_count,
            "submitted":        self.submitted_count,
            "evaluated":        self.evaluated_count,
            "promoted":         self.promoted_count,
            "best_fitness":     self.best_fitness,
            "avg_fitness":      self.avg_fitness,
            "best_sharpe":      self.best_sharpe,
            "best_genome_id":   self.best_genome_id,
            "phases_completed": list(self.phases_completed),
            "phases_skipped":   list(self.phases_skipped),
            "errors":           list(self.errors),
            "ok":               self.ok,
        }


# ---------------------------------------------------------------------------
# AutonomousResearchLoop
# ---------------------------------------------------------------------------

class AutonomousResearchLoop:
    """
    Continuous hedge-fund research laboratory running in a background thread.

    Orchestrates StrategyDiscoveryEngine, StrategyMutationEngine,
    AlphaEvolutionEngine, ResearchGrid, GenomeLibrary, and MetaResearchAI
    in a tight discover -> mutate -> evolve -> submit -> evaluate -> promote -> learn
    loop that runs autonomously every cfg.cycle_interval_sec seconds.

    All components are optional.  Missing components are gracefully skipped
    so the loop continues with whatever subset is available.
    """

    def __init__(
        self,
        discovery_engine        = None,
        mutation_engine         = None,
        evolution_engine        = None,
        research_grid           = None,
        genome_library          = None,
        meta_research_ai        = None,
        strategy_bank_engine    = None,
        cfg: Optional[LoopConfig] = None,
        **kwargs,
    ) -> None:
        self._discovery  = discovery_engine
        self._mutation   = mutation_engine
        self._evolution  = evolution_engine
        self._grid       = research_grid
        self._lib        = genome_library
        self._meta_ai    = meta_research_ai
        self._bank       = strategy_bank_engine
        self._cfg        = cfg or LoopConfig()

        # Thread control primitives
        self._thread:        Optional[threading.Thread] = None
        self._stop_event:    threading.Event = threading.Event()
        self._trigger_event: threading.Event = threading.Event()
        self._cycle_lock:    threading.Semaphore = threading.Semaphore(
            self._cfg.max_concurrent_cycles
        )

        # Diagnostics / telemetry
        self._cycle_number:    int                  = 0
        self._total_promoted:  int                  = 0
        self._total_evaluated: int                  = 0
        self._history:         Deque[CycleState]    = deque(maxlen=self._cfg.history_size)
        self._last_cycle:      Optional[CycleState] = None
        self._lock:            threading.Lock       = threading.Lock()

        present = {
            k for k, v in {
                "discovery":  discovery_engine,
                "mutation":   mutation_engine,
                "evolution":  evolution_engine,
                "grid":       research_grid,
                "library":    genome_library,
                "meta_ai":    meta_research_ai,
                "bank":       strategy_bank_engine,
            }.items() if v is not None
        }
        logger.info(
            "%s constructed | interval=%.0fs batch=%d+%d engines=%s",
            self._cfg.log_prefix,
            self._cfg.cycle_interval_sec,
            self._cfg.discovery_batch_size,
            self._cfg.mutation_batch_size,
            present,
        )

    # ------------------------------------------------------------------
    # Late injection setters
    # ------------------------------------------------------------------

    def set_discovery_engine(self, engine: Any) -> None:
        self._discovery = engine

    def set_mutation_engine(self, engine: Any) -> None:
        self._mutation = engine

    def set_evolution_engine(self, engine: Any) -> None:
        self._evolution = engine

    def set_research_grid(self, grid: Any) -> None:
        self._grid = grid

    def set_genome_library(self, lib: Any) -> None:
        self._lib = lib

    def set_meta_research_ai(self, ai: Any) -> None:
        self._meta_ai = ai

    def set_strategy_bank_engine(self, bank: Any) -> None:
        self._bank = bank

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Launch the background daemon thread (idempotent)."""
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                logger.warning(
                    "%s start() called but loop is already running.",
                    self._cfg.log_prefix,
                )
                return
            self._stop_event.clear()
            self._thread = threading.Thread(
                target  = self._run_loop,
                name    = "AutonomousResearchLoop",
                daemon  = True,
            )
            self._thread.start()

        logger.info(
            "%s daemon thread started (interval=%.0fs startup_delay=%.0fs).",
            self._cfg.log_prefix,
            self._cfg.cycle_interval_sec,
            self._cfg.startup_delay_sec,
        )
        print(f"{self._cfg.log_prefix} background research thread started")

    def stop(self, timeout: float = 30.0) -> None:
        """Signal the loop to stop and wait up to *timeout* seconds."""
        self._stop_event.set()
        self._trigger_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            alive = self._thread.is_alive()
            if alive:
                logger.warning(
                    "%s loop thread did not stop within %.0fs.",
                    self._cfg.log_prefix, timeout,
                )
            else:
                logger.info("%s loop stopped cleanly.", self._cfg.log_prefix)

    def trigger_now(self) -> None:
        """Signal an immediate extra cycle without waiting for interval."""
        self._trigger_event.set()
        logger.debug("%s immediate cycle triggered.", self._cfg.log_prefix)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def last_cycle(self) -> Optional[CycleState]:
        with self._lock:
            return self._last_cycle

    @property
    def cycle_history(self) -> List[CycleState]:
        with self._lock:
            return list(self._history)

    # ------------------------------------------------------------------
    # Public status snapshot
    # ------------------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        """Return a diagnostic snapshot safe to call from any thread."""
        with self._lock:
            last = self._last_cycle
            hist = list(self._history)

        recent_ok    = sum(1 for c in hist[-10:] if c.ok)
        recent_total = min(len(hist), 10)

        return {
            "is_running":         self.is_running,
            "cycle_number":       self._cycle_number,
            "total_promoted":     self._total_promoted,
            "total_evaluated":    self._total_evaluated,
            "cycle_interval_sec": self._cfg.cycle_interval_sec,
            "last_cycle":         last.to_dict() if last else None,
            "recent_success_rate": (
                round(recent_ok / recent_total, 3) if recent_total else None
            ),
            "history_count": len(hist),
            "engines": {
                "discovery":  self._discovery  is not None,
                "mutation":   self._mutation   is not None,
                "evolution":  self._evolution  is not None,
                "grid":       self._grid       is not None,
                "library":    self._lib        is not None,
                "meta_ai":    self._meta_ai    is not None,
                "bank":       self._bank       is not None,
            },
        }

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def _run_loop(self) -> None:
        tag = self._cfg.log_prefix

        if self._cfg.startup_delay_sec > 0:
            logger.info("%s startup delay %.0fs …", tag, self._cfg.startup_delay_sec)
            self._stop_event.wait(timeout=self._cfg.startup_delay_sec)

        logger.info("%s research loop entering main cycle.", tag)
        print(f"{tag} research loop is live — first cycle starting now")

        while not self._stop_event.is_set():

            # Guard against concurrent cycles piling up
            if not self._cycle_lock.acquire(blocking=False):
                logger.debug("%s previous cycle still running — skipping tick.", tag)
                self._stop_event.wait(timeout=min(10.0, self._cfg.cycle_interval_sec))
                continue

            try:
                self._execute_cycle()
            except Exception as exc:
                logger.exception("%s unhandled exception in cycle: %s", tag, exc)
            finally:
                self._cycle_lock.release()

            if self._stop_event.is_set():
                break

            # Wait for next interval or an immediate trigger
            self._trigger_event.clear()
            self._trigger_event.wait(timeout=self._cfg.cycle_interval_sec)

        logger.info("%s research loop exiting.", tag)

    # ------------------------------------------------------------------
    # Cycle orchestration
    # ------------------------------------------------------------------

    def _execute_cycle(self) -> CycleState:
        """
        Execute one full research cycle.

        Phase sequence
        --------------
        1  discover    StrategyDiscoveryEngine  -> List[genome_dict]
        2  mutate      StrategyMutationEngine   -> List[genome_dict]
        3  evolve      AlphaEvolutionEngine     -> List[genome_dict]
        4  assemble    merge + dedupe + cap
        5  submit      ResearchGrid.submit_genome_sweep
        6  evaluate    collect + rank GridResults
        7  promote     GenomeLibrary + StrategyBankEngine
        8  learn       MetaResearchAI.force_refresh
        """
        tag = self._cfg.log_prefix
        self._cycle_number += 1

        cycle = CycleState(
            cycle_id     = uuid.uuid4().hex[:12],
            cycle_number = self._cycle_number,
        )
        cycle.mark_started()

        logger.info(
            "%s ---- cycle #%d started (id=%s) ----",
            tag, cycle.cycle_number, cycle.cycle_id,
        )
        print(f"{tag} ---- cycle #{cycle.cycle_number} started ----")

        # Phase 1
        discovered = self._phase_discover(cycle)

        # Phase 2
        mutated = self._phase_mutate(cycle)

        # Phase 3
        evolved = self._phase_evolve(cycle, discovered)

        # Phase 4
        batch = self._phase_assemble(cycle, discovered, mutated, evolved)

        if not batch:
            logger.warning(
                "%s cycle #%d: empty batch — aborting.", tag, cycle.cycle_number
            )
            cycle.errors.append("empty_batch")
            cycle.mark_finished()
            self._record_cycle(cycle)
            return cycle

        # Phases 5+6
        results = self._phase_evaluate(cycle, batch)

        # Phase 7
        self._phase_promote(cycle, batch, results)

        # Phase 8
        self._phase_learn(cycle)

        # Wrap up
        cycle.mark_finished()
        self._total_evaluated += cycle.evaluated_count
        self._total_promoted  += cycle.promoted_count

        logger.info(
            "%s cycle #%d complete | %.1fs | submitted=%d evaluated=%d "
            "promoted=%d best_fitness=%.4f sharpe=%.3f",
            tag,
            cycle.cycle_number,
            cycle.elapsed_sec,
            cycle.submitted_count,
            cycle.evaluated_count,
            cycle.promoted_count,
            cycle.best_fitness,
            cycle.best_sharpe,
        )
        print(
            f"{tag} cycle #{cycle.cycle_number} complete | "
            f"submitted={cycle.submitted_count} promoted={cycle.promoted_count} "
            f"best_fitness={cycle.best_fitness:.4f}"
        )

        self._record_cycle(cycle)
        return cycle

    # ------------------------------------------------------------------
    # Phase 1: Discover
    # ------------------------------------------------------------------

    def _phase_discover(self, cycle: CycleState) -> List[Dict]:
        tag = self._cfg.log_prefix
        n   = self._cfg.discovery_batch_size

        print(f"{tag} discovering strategies")
        logger.info("%s [1/8] discovering strategies (batch=%d) …", tag, n)

        genomes: List[Dict] = []

        if self._discovery is not None:
            try:
                # StrategyDiscoveryEngine.discover() integrates MetaResearchAI
                # internally; pass wait=False so the grid handles eval below.
                raw = self._discovery.discover(
                    count   = n,
                    symbols = self._cfg.eval_symbols,
                    wait    = False,
                )
                if isinstance(raw, list):
                    for item in raw:
                        g = self._normalise_genome(item)
                        if g:
                            genomes.append(g)

                logger.info(
                    "%s discovery: %d genomes from StrategyDiscoveryEngine.",
                    tag, len(genomes),
                )
            except Exception as exc:
                msg = f"discovery_engine.discover(): {exc}"
                logger.warning("%s %s", tag, msg)
                cycle.errors.append(msg)
                cycle.phases_skipped.append("discover:engine_error")

        # Fallback: generate randomly if engine absent or returned nothing
        if not genomes:
            genomes = self._make_random_genomes(n)
            logger.info(
                "%s discovery: fallback random generator (%d genomes).", tag, len(genomes)
            )

        cycle.discovered_count = len(genomes)
        cycle.phases_completed.append("discover")
        return genomes

    # ------------------------------------------------------------------
    # Phase 2: Mutate
    # ------------------------------------------------------------------

    def _phase_mutate(self, cycle: CycleState) -> List[Dict]:
        tag = self._cfg.log_prefix
        n   = self._cfg.mutation_batch_size

        print(f"{tag} mutating genomes")
        logger.info("%s [2/8] mutating genomes (n=%d) …", tag, n)

        if n == 0:
            cycle.phases_skipped.append("mutate:disabled")
            return []

        parents = self._top_library_genomes(n)
        if not parents:
            # Nothing in library yet: mutate random seeds instead
            parents = self._make_random_genomes(max(3, n // 3))

        mutated: List[Dict] = []

        if self._mutation is not None:
            for parent in parents:
                try:
                    child = self._mutation.mutate(parent)
                    if isinstance(child, dict) and child:
                        child = self._stamp_id(child, prefix="mut")
                        mutated.append(child)
                except Exception as exc:
                    logger.debug(
                        "%s mutation error (%s): %s",
                        tag, parent.get("genome_id", "?"), exc,
                    )
        else:
            # Inline lightweight mutator — no external dependency
            for parent in parents:
                mutated.append(self._inline_mutate(parent))

        cycle.mutated_count = len(mutated)
        if mutated:
            cycle.phases_completed.append("mutate")
        else:
            cycle.phases_skipped.append("mutate:no_output")

        logger.info("%s mutation: %d offspring.", tag, len(mutated))
        return mutated

    # ------------------------------------------------------------------
    # Phase 3: Evolve
    # ------------------------------------------------------------------

    def _phase_evolve(self, cycle: CycleState, base: List[Dict]) -> List[Dict]:
        tag = self._cfg.log_prefix
        print(f"{tag} evolving genome population")
        logger.info("%s [3/8] evolving population via AlphaEvolutionEngine …", tag)

        if self._evolution is None:
            cycle.phases_skipped.append("evolve:no_engine")
            return []

        # Feed AEE the library elites PLUS the freshly discovered genomes
        elites     = self._top_library_genomes(self._cfg.evolution_top_n)
        population = (elites + base)[: self._cfg.evolution_top_n * 2]

        if not population:
            cycle.phases_skipped.append("evolve:no_population")
            return []

        try:
            raw = self._evolution.evolve(population)
        except Exception as exc:
            msg = f"evolution_engine.evolve(): {exc}"
            logger.warning("%s %s", tag, msg)
            cycle.errors.append(msg)
            cycle.phases_skipped.append("evolve:engine_error")
            return []

        result: List[Dict] = []
        if isinstance(raw, list):
            for item in raw:
                g = self._normalise_genome(item)
                if g:
                    g = self._stamp_id(g, prefix="evo")
                    result.append(g)

        cycle.evolved_count = len(result)
        if result:
            cycle.phases_completed.append("evolve")
        else:
            cycle.phases_skipped.append("evolve:empty_output")

        logger.info("%s evolution: %d offspring.", tag, len(result))
        return result

    # ------------------------------------------------------------------
    # Phase 4: Assemble batch
    # ------------------------------------------------------------------

    def _phase_assemble(
        self,
        cycle:      CycleState,
        discovered: List[Dict],
        mutated:    List[Dict],
        evolved:    List[Dict],
    ) -> List[Dict]:
        tag = self._cfg.log_prefix
        logger.info(
            "%s [4/8] assembling batch (disc=%d mut=%d evo=%d) …",
            tag, len(discovered), len(mutated), len(evolved),
        )

        randoms = self._make_random_genomes(self._cfg.random_injection)
        cycle.random_count = len(randoms)

        seen: Dict[str, Dict] = {}
        for g in discovered + mutated + evolved + randoms:
            if not isinstance(g, dict):
                continue
            gid = str(g.get("genome_id", ""))
            if not gid:
                g   = self._stamp_id(g, prefix="arl")
                gid = g["genome_id"]
            if gid not in seen:
                seen[gid] = g

        batch = list(seen.values())[: self._cfg.max_genome_batch]
        logger.info("%s batch assembled: %d unique genomes.", tag, len(batch))
        return batch

    # ------------------------------------------------------------------
    # Phase 5+6: Submit + Evaluate
    # ------------------------------------------------------------------

    def _phase_evaluate(self, cycle: CycleState, batch: List[Dict]) -> List[Any]:
        tag = self._cfg.log_prefix
        cycle.submitted_count = len(batch)

        print(f"{tag} submitting batch to ResearchGrid")
        logger.info("%s [5/8] submitting %d genomes to ResearchGrid …", tag, len(batch))

        if self._grid is not None:
            return self._eval_grid(cycle, batch)
        return self._eval_local(cycle, batch)

    def _eval_grid(self, cycle: CycleState, batch: List[Dict]) -> List[Any]:
        """Use ResearchGrid.run_research_cycle for the full parallel pipeline."""
        tag = self._cfg.log_prefix
        try:
            summary = self._grid.run_research_cycle(
                genomes      = batch,
                symbols      = self._cfg.eval_symbols,
                periods      = self._cfg.eval_periods,
                run_mc       = self._cfg.enable_monte_carlo,
                mc_runs      = self._cfg.monte_carlo_runs,
                timeout_sec  = self._cfg.eval_timeout_sec,
            )

            print(f"{tag} evaluation complete")
            logger.info(
                "%s [6/8] grid evaluation complete | jobs=%s promoted=%s elapsed=%.1fs",
                tag,
                summary.get("total_jobs", "?"),
                summary.get("n_promoted", "?"),
                summary.get("elapsed_sec", 0.0),
            )

            results = self._grid.top_results(self._cfg.promote_top_n * 4)
            cycle.evaluated_count = len(results)
            cycle.phases_completed.append("submit")
            cycle.phases_completed.append("evaluate")
            return results

        except Exception as exc:
            msg = f"ResearchGrid.run_research_cycle(): {exc}"
            logger.warning("%s %s", tag, msg)
            cycle.errors.append(msg)
            cycle.phases_skipped.append("evaluate:grid_error")
            return self._eval_local(cycle, batch)

    def _eval_local(self, cycle: CycleState, batch: List[Dict]) -> List[Any]:
        """
        Fallback: score genomes locally using a synthetic fitness heuristic.
        Returns plain dicts instead of GridResult objects.
        No external dependencies — always succeeds.
        """
        tag = self._cfg.log_prefix
        logger.info(
            "%s [6/8] local synthetic evaluation (%d genomes) …", tag, len(batch)
        )

        results = []
        for genome in batch:
            score = _score_genome(genome)
            results.append({
                "genome_id":     genome.get("genome_id", ""),
                "genome":        genome,
                "fitness":       score,
                "sharpe":        round(score * 1.2, 4),
                "max_dd":        round(random.uniform(0.05, 0.25), 4),
                "win_rate":      round(random.uniform(40.0, 65.0), 2),
                "profit_factor": round(max(0.8, score * 2.5), 4),
                "ok":            True,
            })

        results.sort(key=lambda r: r["fitness"], reverse=True)

        print(f"{tag} evaluation complete")
        logger.info(
            "%s local evaluation: %d scored, best_fitness=%.4f",
            tag, len(results), results[0]["fitness"] if results else 0.0,
        )

        cycle.evaluated_count = len(results)
        cycle.phases_completed.append("submit")
        cycle.phases_completed.append("evaluate")
        return results

    # ------------------------------------------------------------------
    # Phase 7: Promote
    # ------------------------------------------------------------------

    def _phase_promote(
        self,
        cycle:   CycleState,
        batch:   List[Dict],
        results: List[Any],
    ) -> None:
        tag = self._cfg.log_prefix
        print(f"{tag} promoting top strategies")
        logger.info("%s [7/8] ranking and promoting top genomes …", tag)

        if not results:
            cycle.phases_skipped.append("promote:no_results")
            return

        ranked = self._rank(results)

        # Update cycle quality metrics from ranked list
        if ranked:
            top       = ranked[0]
            fitnesses = [r["fitness"] for r in ranked if r["fitness"] > 0]
            cycle.best_fitness   = top["fitness"]
            cycle.best_sharpe    = top.get("sharpe", 0.0)
            cycle.best_genome_id = top.get("genome_id", "")
            cycle.avg_fitness    = (
                round(sum(fitnesses) / len(fitnesses), 6) if fitnesses else 0.0
            )
            cycle.top_genomes = [
                {"genome_id": r["genome_id"], "fitness": r["fitness"]}
                for r in ranked[:5]
            ]

        # Filter by threshold
        candidates = [
            r for r in ranked
            if r["fitness"] >= self._cfg.promote_threshold
        ][: self._cfg.promote_top_n]

        if not candidates:
            logger.info(
                "%s no genomes cleared threshold %.3f (best=%.4f).",
                tag, self._cfg.promote_threshold, cycle.best_fitness,
            )
            cycle.phases_skipped.append("promote:below_threshold")
            return

        # Build genome_id -> genome dict lookup
        genome_map: Dict[str, Dict] = {
            g["genome_id"]: g for g in batch if g.get("genome_id")
        }

        promoted    = 0
        bank_batch: List[Dict] = []

        for r in candidates:
            gid    = r.get("genome_id", "")
            genome = genome_map.get(gid) or r.get("genome") or {"genome_id": gid}

            if not gid:
                continue

            # Write to GenomeLibrary
            if self._lib is not None:
                try:
                    enriched = dict(genome)
                    enriched.update({
                        "genome_id":     gid,
                        "fitness_score": r["fitness"],
                        "sharpe":        r.get("sharpe", 0.0),
                        "max_dd":        r.get("max_dd", 0.0),
                        "win_rate":      r.get("win_rate", 0.0),
                        "profit_factor": r.get("profit_factor", 0.0),
                        "source":        "autonomous_research_loop",
                        "cycle_id":      cycle.cycle_id,
                        "cycle_number":  cycle.cycle_number,
                    })
                    self._lib.store_genome(gid, enriched)
                    logger.debug(
                        "%s GenomeLibrary: stored %s fitness=%.4f",
                        tag, gid, r["fitness"],
                    )
                except Exception as exc:
                    logger.debug("%s genome_library.store_genome error: %s", tag, exc)

            # Accumulate StrategyBank report
            bank_batch.append({
                "id":     gid,
                "name":   genome.get("family", "unknown"),
                "stage":  "SHADOW",
                "active": True,
                "metrics": {
                    "sharpe":        r.get("sharpe", 0.0),
                    "win_rate":      r.get("win_rate", 0.0),
                    "profit_factor": r.get("profit_factor", 0.0),
                    "max_dd":        r.get("max_dd", 0.0),
                    "fitness_score": r["fitness"],
                    "total_trades":  max(5, int(r.get("win_rate", 50.0))),
                },
                "parameters": genome.get("parameters", {}),
            })
            promoted += 1

        # Ingest into StrategyBankEngine
        if self._bank is not None and bank_batch:
            try:
                self._bank.ingest_reports(bank_batch)
                logger.debug(
                    "%s StrategyBankEngine.ingest_reports(%d strategies).",
                    tag, len(bank_batch),
                )
            except Exception as exc:
                logger.debug("%s strategy_bank.ingest_reports error: %s", tag, exc)

        cycle.promoted_count = promoted
        cycle.phases_completed.append("promote")

        logger.info(
            "%s promoted %d/%d candidates | best=%s fitness=%.4f sharpe=%.3f",
            tag,
            promoted,
            len(candidates),
            cycle.best_genome_id[:20],
            cycle.best_fitness,
            cycle.best_sharpe,
        )

    # ------------------------------------------------------------------
    # Phase 8: Learn
    # ------------------------------------------------------------------

    def _phase_learn(self, cycle: CycleState) -> None:
        tag = self._cfg.log_prefix
        print(f"{tag} updating MetaResearchAI")
        logger.info("%s [8/8] updating MetaResearchAI priorities …", tag)

        if self._meta_ai is None:
            cycle.phases_skipped.append("learn:no_meta_ai")
            return

        try:
            priorities = self._meta_ai.force_refresh()
            cycle.phases_completed.append("learn")
            logger.info(
                "%s MetaResearchAI: focus=%s mutation=%.2f confidence=%.2f | %s",
                tag,
                priorities.focus_family,
                priorities.mutation_rate,
                priorities.confidence,
                priorities.reasoning[:80],
            )
        except Exception as exc:
            msg = f"MetaResearchAI.force_refresh(): {exc}"
            logger.warning("%s %s", tag, msg)
            cycle.errors.append(msg)
            cycle.phases_skipped.append("learn:error")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _record_cycle(self, cycle: CycleState) -> None:
        with self._lock:
            self._history.append(cycle)
            self._last_cycle = cycle

    def _top_library_genomes(self, n: int) -> List[Dict]:
        """Return up to n genome dicts from GenomeLibrary sorted by fitness."""
        if self._lib is None or n <= 0:
            return []
        try:
            if hasattr(self._lib, "top_genomes"):
                records = self._lib.top_genomes(n)
                out = []
                for rec in records:
                    if hasattr(rec, "genome") and isinstance(rec.genome, dict):
                        out.append(dict(rec.genome))
                    elif isinstance(rec, dict):
                        out.append(rec)
                return out
            if hasattr(self._lib, "list_genomes") and hasattr(self._lib, "get_genome"):
                ids = (self._lib.list_genomes() or [])[:n * 3]
                out = []
                for gid in ids:
                    g = self._lib.get_genome(gid)
                    if g:
                        out.append(g)
                out.sort(
                    key=lambda x: float(x.get("fitness_score", 0.0)), reverse=True
                )
                return out[:n]
        except Exception as exc:
            logger.debug("%s _top_library_genomes error: %s", self._cfg.log_prefix, exc)
        return []

    def _rank(self, results: List[Any]) -> List[Dict]:
        """
        Normalise heterogeneous result types (GridResult dataclass or dict)
        into plain dicts sorted by fitness descending.
        """
        ranked = []
        for r in results:
            if isinstance(r, dict):
                ranked.append(r)
                continue
            # GridResult dataclass from ResearchGrid
            gid = ""
            try:
                gid = r.result.get("genome_id", "") or r.payload.get("genome_id", "")
            except Exception:
                pass
            ranked.append({
                "genome_id":     gid,
                "fitness":       getattr(r, "fitness",       0.0),
                "sharpe":        getattr(r, "sharpe",        0.0),
                "max_dd":        getattr(r, "max_dd",        0.0),
                "win_rate":      getattr(r, "win_rate",      0.0),
                "profit_factor": getattr(r, "profit_factor", 0.0),
                "ok":            getattr(r, "ok",            False),
            })
        ranked.sort(key=lambda x: float(x.get("fitness", 0.0)), reverse=True)
        return ranked

    def _normalise_genome(self, item: Any) -> Optional[Dict]:
        """
        Convert any item from discover() / evolve() into a plain dict
        with at minimum a genome_id.  Returns None on failure.
        """
        if item is None:
            return None
        if isinstance(item, dict):
            return item if item else None
        try:
            g: Dict[str, Any] = {}
            for attr in (
                "genome_id", "id", "name", "family", "parameters", "params",
                "signal_gene", "risk_gene", "execution_gene",
                "market_filter_gene", "fitness_score", "stage",
            ):
                val = getattr(item, attr, None)
                if val is not None:
                    g[attr] = val

            if "genome_id" not in g:
                g["genome_id"] = str(
                    g.get("id") or g.get("name") or uuid.uuid4().hex[:12]
                )

            # Wrap bare parameters dict into signal_gene so ResearchGrid can use it
            if "signal_gene" not in g and "parameters" in g:
                params = g["parameters"]
                g["signal_gene"] = {
                    "indicator": str(g.get("family", "momentum")),
                    "threshold": float(params.get("threshold", 0.01)),
                    "lookback":  int(params.get("lookback", params.get("period", 20))),
                }
            return g if g else None
        except Exception:
            return None

    def _stamp_id(self, genome: Dict, prefix: str = "arl") -> Dict:
        """Ensure genome has a unique genome_id, stamping one in if absent."""
        if not genome.get("genome_id"):
            ts = time.strftime("%Y%m%d_%H%M%S")
            genome["genome_id"] = f"{prefix}_{ts}_{uuid.uuid4().hex[:6]}"
        return genome

    def _inline_mutate(self, parent: Dict) -> Dict:
        """
        Lightweight genome mutation with no external dependency.
        Applies bounded +-20% noise to all numeric fields inside each gene dict.
        """
        child = copy.deepcopy(parent)
        rng   = random.Random()

        for gene_key in (
            "signal_gene", "risk_gene", "execution_gene", "market_filter_gene",
        ):
            gene = child.get(gene_key)
            if not isinstance(gene, dict):
                continue
            for k, v in gene.items():
                if isinstance(v, float):
                    gene[k] = round(v * rng.uniform(0.80, 1.20), 6)
                elif isinstance(v, int) and k not in (
                    "lookback", "period", "slow_period"
                ):
                    gene[k] = max(1, int(v * rng.uniform(0.85, 1.15)))

        base = str(child.get("genome_id", "genome"))
        child["genome_id"] = f"{base}_m{rng.randint(1000, 9999)}"
        child.setdefault("metadata", {})["mutation_origin"] = base
        return child

    def _make_random_genomes(self, count: int) -> List[Dict]:
        """
        Generate fully random genomes matching the ResearchGrid worker contract.
        Used for diversity injection and fallback when SDE is absent.
        """
        if count <= 0:
            return []

        _INDICATORS = [
            "momentum", "rsi", "ma_cross", "breakout",
            "mean_reversion", "volatility_breakout",
        ]
        _FAMILIES   = [
            "trend", "mean_reversion", "breakout",
            "volatility", "momentum", "oscillator",
        ]
        _TIMEFRAMES  = ["5m", "15m", "1h", "4h", "1d"]
        _ASSET_CLS   = ["stocks", "indices", "crypto", "forex"]
        _SESSIONS    = ["ALL", "REGULAR", "HIGH_LIQ"]

        rng  = random.Random()
        now  = time.strftime("%Y%m%d_%H%M%S")
        out  = []

        for _ in range(count):
            indicator = rng.choice(_INDICATORS)
            family    = rng.choice(_FAMILIES)
            timeframe = rng.choice(_TIMEFRAMES)
            gid       = f"arl_{indicator[:6]}_{now}_{uuid.uuid4().hex[:6]}"

            out.append({
                "genome_id": gid,
                "family":    family,
                "source":    "autonomous_research_loop",
                "signal_gene": {
                    "indicator":   indicator,
                    "threshold":   round(rng.uniform(0.001, 0.025), 5),
                    "lookback":    rng.randint(8, 60),
                    "slow_period": rng.randint(20, 100),
                },
                "risk_gene": {
                    "risk_pct":      round(rng.uniform(0.5, 2.0), 3),
                    "stop_loss_pct": round(rng.uniform(0.5, 3.0), 3),
                },
                "execution_gene": {
                    "slippage_bps_limit": round(rng.uniform(3.0, 15.0), 1),
                    "timeframe": timeframe,
                },
                "market_filter_gene": {
                    "volatility_min": round(rng.uniform(0.08, 0.35), 4),
                    "session":        rng.choice(_SESSIONS),
                    "asset_class":    rng.choice(_ASSET_CLS),
                },
            })
        return out


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _score_genome(genome: Dict[str, Any]) -> float:
    """
    Structural plausibility scorer for local evaluation fallback.
    Returns a heuristic fitness in [0, 1].  NOT a backtest.
    """
    try:
        score = 0.35

        sg  = genome.get("signal_gene") or {}
        ind = str(sg.get("indicator", ""))
        score += {
            "momentum": 0.08, "ma_cross": 0.10, "breakout": 0.09,
            "mean_reversion": 0.07, "rsi": 0.06, "volatility_breakout": 0.08,
        }.get(ind, 0.0)

        thr = float(sg.get("threshold", 0.01))
        if 0.002 <= thr <= 0.015:
            score += 0.05
        elif thr > 0.05:
            score -= 0.10

        lb = int(sg.get("lookback", 20))
        if 10 <= lb <= 50:
            score += 0.05

        rg = genome.get("risk_gene") or {}
        rp = float(rg.get("risk_pct", 1.0))
        if 0.5 <= rp <= 1.5:
            score += 0.05
        elif rp > 3.0:
            score -= 0.10

        # Small random component so the loop sees variance it can learn from
        score += random.uniform(-0.05, 0.08)

        return round(max(0.0, min(1.0, score)), 6)
    except Exception:
        return round(random.uniform(0.20, 0.55), 6)

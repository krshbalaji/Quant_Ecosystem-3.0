"""
quant_ecosystem.research.grid
==============================
Parallel research grid package.

Exports
-------
ResearchGrid
    Production-grade CPU-parallel strategy evaluation grid.
    Evaluates hundreds of genomes per minute using all available CPU cores
    via ``ProcessPoolExecutor`` (with transparent ``ThreadPoolExecutor``
    fallback when fork/spawn is unavailable).

JobType
    Enum of supported job types:
    GENOME_BACKTEST, GENOME_SWEEP, PARAMETER_SWEEP,
    WALK_FORWARD_BATCH, MONTE_CARLO, FACTOR_BACKTEST,
    SHADOW_EVAL, CROSS_VALIDATION.

GridJob / GridResult
    Dataclasses for work units and results.

Example
-------
>>> from quant_ecosystem.research.grid import ResearchGrid
>>> grid = ResearchGrid(n_workers=4, promote_threshold=0.5)
>>> grid.start()
>>> job_ids = grid.submit_genome_sweep(genomes, symbols=["NSE:INFY"])
>>> top = grid.top_results(20)
"""

from __future__ import annotations

from quant_ecosystem.research.grid.parallel_research_grid import (  # noqa: F401
    GridJob,
    GridResult,
    GridScheduler,
    JobStatus,
    JobType,
    ParallelWorkerPool,
    ResearchGrid,
    ResultStore,
)

__all__ = [
    "ResearchGrid",
    "GridJob",
    "GridResult",
    "JobType",
    "JobStatus",
    "ResultStore",
    "ParallelWorkerPool",
    "GridScheduler",
]

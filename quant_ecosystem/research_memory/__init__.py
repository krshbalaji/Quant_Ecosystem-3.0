"""
quant_ecosystem/research_memory/__init__.py
============================================
Persistent Research Memory Layer — Quant Ecosystem 3.0

Exports the five core sub-systems and the unified ResearchMemoryLayer façade.

Recommended entry point:
    from quant_ecosystem.research_memory import ResearchMemoryLayer
    layer = ResearchMemoryLayer(config={"RESEARCH_MEMORY_ROOT": "data/research_memory"})

Direct sub-system access:
    from quant_ecosystem.research_memory import AlphaMemoryStore, AlphaRecord
    from quant_ecosystem.research_memory import ExperimentTracker, ExperimentType
    from quant_ecosystem.research_memory import StrategyGenealogy, GenealogyNode
    from quant_ecosystem.research_memory import PerformanceArchive, PerformanceSlice
    from quant_ecosystem.research_memory import SnapshotStore
"""

from quant_ecosystem.research_memory.layer import ResearchMemoryLayer

from quant_ecosystem.research_memory.alpha_memory_store import (
    AlphaMemoryStore,
    AlphaRecord,
    AlphaMemoryIndex,
)

from quant_ecosystem.research_memory.experiment_tracker import (
    ExperimentTracker,
    ExperimentRecord,
    ExperimentType,
    ExperimentStatus,
    RunManifest,
)

from quant_ecosystem.research_memory.strategy_genealogy import (
    StrategyGenealogy,
    GenealogyNode,
    GenealogyTree,
)

from quant_ecosystem.research_memory.performance_archive import (
    PerformanceArchive,
    PerformanceSlice,
    RegimePerformance,
    StrategyArchive,
)

from quant_ecosystem.research_memory.research_snapshot import (
    SnapshotStore,
    SnapshotManifest,
    ResearchSnapshot,
)

__all__ = [
    # Façade
    "ResearchMemoryLayer",

    # Alpha
    "AlphaMemoryStore",
    "AlphaRecord",
    "AlphaMemoryIndex",

    # Experiments
    "ExperimentTracker",
    "ExperimentRecord",
    "ExperimentType",
    "ExperimentStatus",
    "RunManifest",

    # Genealogy
    "StrategyGenealogy",
    "GenealogyNode",
    "GenealogyTree",

    # Performance
    "PerformanceArchive",
    "PerformanceSlice",
    "RegimePerformance",
    "StrategyArchive",

    # Snapshots
    "SnapshotStore",
    "SnapshotManifest",
    "ResearchSnapshot",
]

"""quant_ecosystem/autonomous_research — Autonomous hedge-fund research loop."""

from .autonomous_research_loop import (
    AutonomousResearchLoop,
    CycleState,
    LoopConfig,
)


from quant_ecosystem.autonomous_research.signal_decay_engine import (
    SignalDecayEngine,
    signal_decay_engine,
)

from quant_ecosystem.autonomous_research.opportunity_aging_engine import (
    OpportunityAgingEngine,
    opportunity_aging_engine,
)

from quant_ecosystem.autonomous_research.research_memory import (
    ResearchMemory,
    research_memory,
)

from quant_ecosystem.autonomous_research.adaptive_weight_engine import (
    AdaptiveWeightEngine,
    adaptive_weight_engine,
)

from quant_ecosystem.autonomous_research.alpha_evolution_memory import (
    AlphaEvolutionMemory,
    alpha_evolution_memory,
)

from quant_ecosystem.autonomous_research.autonomous_research_loop_controller import (
    AutonomousResearchLoopController,
    autonomous_research_loop_controller,
)

__all__ = [
    "AutonomousResearchLoop",
    "CycleState", "LoopConfig"
    "SignalDecayEngine",
    "signal_decay_engine",
    "OpportunityAgingEngine",
    "opportunity_aging_engine",
    "ResearchMemory",
    "research_memory",
    "AdaptiveWeightEngine",
    "adaptive_weight_engine",
    "AlphaEvolutionMemory",
    "alpha_evolution_memory",
    "AutonomousResearchLoopController",
    "autonomous_research_loop_controller",
]
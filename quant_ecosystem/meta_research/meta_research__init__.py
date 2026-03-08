"""
quant_ecosystem.meta_research
==============================
Meta-Research AI layer — guides StrategyDiscoveryEngine with data-driven
research priorities derived from GenomeLibrary, ResearchGrid results, and
live PerformanceStore trade data.

Exports
-------
MetaResearchAI      Main analysis engine.
ResearchPriorities  Typed output dataclass with .to_dict() method.
"""

from quant_ecosystem.meta_research.meta_research_ai import (  # noqa: F401
    MetaResearchAI,
    ResearchPriorities,
)

__all__ = ["MetaResearchAI", "ResearchPriorities"]

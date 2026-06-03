from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Sequence, Tuple

from .governance_observation import GovernanceObservation
from .governance_observability_registry import GovernanceObservabilityRegistry
from .knowledge_pattern import KnowledgePattern


class GovernanceObservabilityEngine:

    def observe(
        self,
        pattern: KnowledgePattern,
        observation_id: str,
        summary: Optional[str] = None,
        status: str = "OK",
        issues: Optional[Sequence[str]] = None,
        metadata: Optional[Dict[str, object]] = None,
    ) -> GovernanceObservation:
        observation = GovernanceObservation(
            observation_id=observation_id,
            timestamp=datetime.utcnow(),
            pattern_id=pattern.pattern_id,
            category=pattern.category,
            source_keys=pattern.source_keys,
            lineage_ids=tuple(
                key
                for key in pattern.source_keys
                if "audit.execution.lineage." in key
            ),
            status=status,
            summary=summary,
            issues=tuple(issues or []),
            metadata={
                **(metadata or {}),
                "frequency": pattern.frequency,
                "aggregated_count": pattern.aggregated_count,
            },
        )
        return observation

    def register_observation(
        self,
        registry: GovernanceObservabilityRegistry,
        observation: GovernanceObservation,
    ) -> None:
        registry.register(observation)

    def summarize_evolution(
        self,
        observations: Sequence[GovernanceObservation],
    ) -> Dict[str, Dict[str, int]]:
        summary: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for observation in observations:
            category = observation.category or "unknown"
            summary[category][observation.status] += 1
            summary[category]["total"] += 1
        return {category: dict(status_counts) for category, status_counts in summary.items()}

    def trace_origins(
        self,
        pattern: KnowledgePattern,
    ) -> Dict[str, Sequence[str]]:
        return {
            "source_keys": list(pattern.source_keys),
            "provenance": list(pattern.provenance),
            "lineage_ids": [key for key in pattern.source_keys if "audit.execution.lineage." in key],
        }

    def aggregate_observations(
        self,
        observations: Sequence[GovernanceObservation],
    ) -> GovernanceObservation:
        aggregated_ids = ",".join(obs.observation_id for obs in observations)
        categories = sorted({obs.category for obs in observations if obs.category})
        statuses = sorted({obs.status for obs in observations})
        issues = sorted({issue for obs in observations for issue in obs.issues})
        source_keys = tuple(
            sorted({key for obs in observations for key in obs.source_keys})
        )
        lineage_ids = tuple(
            sorted({key for obs in observations for key in obs.lineage_ids})
        )

        return GovernanceObservation(
            observation_id=f"aggregate:{aggregated_ids}",
            timestamp=datetime.utcnow(),
            pattern_id=None,
            category=categories[0] if categories else None,
            source_keys=source_keys,
            lineage_ids=lineage_ids,
            status=",".join(statuses),
            summary=f"Aggregated {len(observations)} observations",
            issues=tuple(issues),
            metadata={
                "observation_count": len(observations),
            },
        )

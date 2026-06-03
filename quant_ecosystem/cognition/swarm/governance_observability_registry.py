from typing import Dict, List, Optional

from .governance_observation import GovernanceObservation


class GovernanceObservabilityRegistry:

    def __init__(self) -> None:
        self._observations: Dict[str, GovernanceObservation] = {}

    def register(
        self,
        observation: GovernanceObservation,
    ) -> None:
        self._observations[observation.observation_id] = observation

    def get(
        self,
        observation_id: str,
    ) -> Optional[GovernanceObservation]:
        return self._observations.get(observation_id)

    def all(
        self,
    ) -> List[GovernanceObservation]:
        return list(self._observations.values())

    def count(
        self,
    ) -> int:
        return len(self._observations)

    def clear(
        self,
    ) -> None:
        self._observations.clear()

    def find_by_pattern(
        self,
        pattern_id: str,
    ) -> List[GovernanceObservation]:
        return [
            obs
            for obs in self._observations.values()
            if obs.pattern_id == pattern_id
        ]

    def find_by_status(
        self,
        status: str,
    ) -> List[GovernanceObservation]:
        return [
            obs
            for obs in self._observations.values()
            if obs.status == status
        ]

    def keys(self) -> List[str]:
        return list(self._observations.keys())

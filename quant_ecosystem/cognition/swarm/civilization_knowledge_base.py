from typing import Dict, List

from .federation_observation import FederationObservation


class CivilizationKnowledgeBase:

    def __init__(self):
        self._observations: List[FederationObservation] = []

    def add(
        self,
        observation: FederationObservation,
    ) -> None:

        self._observations.append(observation)

    def observations(self):

        return list(self._observations)

    def count(self):

        return len(self._observations)
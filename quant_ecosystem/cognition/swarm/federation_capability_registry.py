from typing import Dict

from .federation_capability import (
    FederationCapability,
)


class FederationCapabilityRegistry:

    def __init__(self):
        self._capabilities: Dict[
            str,
            FederationCapability,
        ] = {}

    def register(
        self,
        capability: FederationCapability,
    ) -> None:

        self._capabilities[
            capability.capability_id
        ] = capability

    def count(self) -> int:

        return len(
            self._capabilities
        )

    def active_count(self) -> int:

        return sum(
            1
            for capability
            in self._capabilities.values()
            if capability.active
        )

    def capabilities(
        self,
    ):

        return list(
            self._capabilities.values()
        )   
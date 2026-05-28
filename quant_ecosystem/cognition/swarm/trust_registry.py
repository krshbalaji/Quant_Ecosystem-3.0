from typing import Dict

from .federation_identity import FederationIdentity


class TrustRegistry:

    def __init__(self):
        self._registry: Dict[str, FederationIdentity] = {}

    def register(self, identity: FederationIdentity) -> None:
        self._registry[identity.organism_id] = identity

    def get(self, organism_id: str):
        return self._registry.get(organism_id)

    def is_known(self, organism_id: str) -> bool:
        return organism_id in self._registry

    def evaluate_trust(
        self,
        organism_id: str,
        capability: str,
    ) -> bool:

        identity = self.get(organism_id)

        if identity is None:
            return False

        return identity.is_trusted_for(capability)
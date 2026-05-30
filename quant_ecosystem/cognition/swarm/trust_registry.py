from .federation_identity import FederationIdentity

from quant_ecosystem.core.registry_threading import (
    ThreadSafeRegistry,
)


class TrustRegistry(
    ThreadSafeRegistry[
        str,
        FederationIdentity,
    ]
):

    def register(
        self,
        identity: FederationIdentity,
    ) -> None:

        if self.exists(identity.organism_id):
            return

        super().register(
            identity.organism_id,
            identity,
        )

    def get(
        self,
        organism_id: str,
    ):

        if not self.exists(organism_id):
            return None

        return super().get(
            organism_id,
        )

    def is_known(
        self,
        organism_id: str,
    ) -> bool:

        return self.exists(
            organism_id,
        )

    def evaluate_trust(
        self,
        organism_id: str,
        capability: str,
    ) -> bool:

        identity = self.get(
            organism_id,
        )

        if identity is None:
            return False

        return identity.is_trusted_for(
            capability,
        )
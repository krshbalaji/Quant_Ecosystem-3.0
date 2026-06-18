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
        identity_or_key,
        value=None,
    ):
        if value is None:
            super().register(
                identity_or_key.organism_id,
                identity_or_key,
            )
        else:
            super().register(
                identity_or_key,
                value,
            )

    def get(
        self,
        key: str,
    ) -> FederationIdentity:
        return super().get(key)

    def register_identity(
        self,
        identity: FederationIdentity,
    ) -> None:

        if self.exists(identity.organism_id):
            return

        self.register(
            identity.organism_id,
            identity,
        )

    def get_identity(
        self,
        organism_id: str,
    ) -> FederationIdentity | None:

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

        identity = self.get_identity(
            organism_id,
        )

        if identity is None:
            return False

        return identity.is_trusted_for(
            capability,
        )
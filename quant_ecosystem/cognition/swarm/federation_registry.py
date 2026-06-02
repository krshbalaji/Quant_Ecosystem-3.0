from quant_ecosystem.core.keyed_registry import (
    KeyedRegistry,
)

from .federation_entity import (
    FederationEntity,
)


class FederationRegistry(
    KeyedRegistry[
        str,
        FederationEntity,
    ]
):

    def register(
        self,
        entity: FederationEntity,
    ) -> None:

        super().register(
            entity.entity_id,
            entity,
        )
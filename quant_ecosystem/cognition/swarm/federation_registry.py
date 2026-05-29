from typing import Dict

from .federation_entity import (
    FederationEntity,
)


class FederationRegistry:

    def __init__(self):
        self._entities: Dict[
            str,
            FederationEntity,
        ] = {}

    def register(
        self,
        entity: FederationEntity,
    ) -> None:

        self._entities[
            entity.entity_id
        ] = entity

    def count(self) -> int:

        return len(
            self._entities
        )
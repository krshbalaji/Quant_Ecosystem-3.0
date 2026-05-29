from dataclasses import dataclass


@dataclass(frozen=True)
class FederationEntity:
    entity_id: str
    entity_type: str
from dataclasses import dataclass


@dataclass(frozen=True)
class FederationComponent:
    component_id:str
    component_type: str
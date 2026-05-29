from dataclasses import dataclass


@dataclass(frozen=True)
class FederationContract:
    contract_id: str
    active: bool = True
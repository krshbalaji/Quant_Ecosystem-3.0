from dataclasses import dataclass


@dataclass(frozen=True)
class AuthorizationTrace:
    authorization_id: str
    lineage_id: str
    approved: bool
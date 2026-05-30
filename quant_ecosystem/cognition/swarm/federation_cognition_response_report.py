from dataclasses import dataclass


@dataclass(frozen=True)
class FederationCognitionResponseReport:
    recommended_action: str
    response_count: int
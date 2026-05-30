from dataclasses import dataclass


@dataclass(frozen=True)
class FederationCognitionGovernanceRequest:
    recommended_action: str
    source_workflow: str
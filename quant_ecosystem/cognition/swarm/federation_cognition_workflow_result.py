from dataclasses import dataclass


@dataclass(frozen=True)
class FederationCognitionWorkflowResult:
    workflow_name: str
    accepted: bool
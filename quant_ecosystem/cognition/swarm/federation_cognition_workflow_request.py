from dataclasses import dataclass


@dataclass(frozen=True)
class FederationCognitionWorkflowRequest:
    workflow_name: str
    action: str
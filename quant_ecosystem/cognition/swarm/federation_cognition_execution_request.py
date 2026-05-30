from dataclasses import dataclass


@dataclass(frozen=True)
class FederationCognitionExecutionRequest:
    action: str
    workflow_name: str
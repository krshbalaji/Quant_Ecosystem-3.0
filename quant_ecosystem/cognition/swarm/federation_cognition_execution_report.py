from dataclasses import dataclass


@dataclass(frozen=True)
class FederationCognitionExecutionReport:
    workflow_name: str
    action: str
    execution_ready: bool
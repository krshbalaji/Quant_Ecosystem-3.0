from dataclasses import dataclass


@dataclass(frozen=True)
class OrchestrationStage:
    stage_name: str
    enabled: bool = True
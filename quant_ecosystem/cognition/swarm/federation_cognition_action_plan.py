from dataclasses import dataclass

from .federation_cognition_action_step import (
    FederationCognitionActionStep,
)


@dataclass(frozen=True)
class FederationCognitionActionPlan:
    action: str
    steps: list[FederationCognitionActionStep]
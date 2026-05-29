from dataclasses import dataclass

from .initiative_lifecycle_state import (
    InitiativeLifecycleState,
)


@dataclass(frozen=True)
class InitiativeLifecycleRecord:
    initiative_id: str
    state: InitiativeLifecycleState
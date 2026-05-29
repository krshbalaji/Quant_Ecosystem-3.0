from enum import Enum


class InitiativeLifecycleState(str, Enum):
    PROPOSED = "proposed"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    AUTHORIZED = "authorized"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"
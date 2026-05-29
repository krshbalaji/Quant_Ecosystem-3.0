from enum import Enum


class ArchitectureCategory(str, Enum):
    GOVERNANCE = "governance"
    COGNITION = "cognition"
    TOPOLOGY = "topology"
    LIFECYCLE = "lifecycle"
    EXECUTION = "execution"
    ANALYTICS = "analytics"
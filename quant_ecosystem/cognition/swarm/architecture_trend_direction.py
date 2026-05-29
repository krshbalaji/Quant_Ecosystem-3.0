from enum import Enum


class ArchitectureTrendDirection(str, Enum):
    GROWING = "growing"
    STABLE = "stable"
    DECLINING = "declining"
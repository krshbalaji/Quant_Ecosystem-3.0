from __future__ import annotations

from enum import Enum
from typing import Any

from quant_ecosystem.contracts.position import Position


class LifecycleState(str, Enum):
    NEW = "NEW"
    BUILDING = "BUILDING"
    ACTIVE = "ACTIVE"
    MATURE = "MATURE"
    DISTRIBUTION = "DISTRIBUTION"
    EXITING = "EXITING"
    RETIRED = "RETIRED"


def _to_position(position: Any) -> Position:
    if isinstance(position, Position):
        return position
    if isinstance(position, dict):
        return Position.from_mapping(position)
    raise TypeError("position must be a Position or dict mapping")


def infer_lifecycle(position: Any) -> LifecycleState:
    position = _to_position(position)
    lifecycle_name = str(position.lifecycle or "").upper()
    if lifecycle_name == "RETIRED":
        return LifecycleState.RETIRED
    if lifecycle_name == "EXITING":
        return LifecycleState.EXITING

    thesis_stage = str(position.thesis.get("stage", "")).upper()
    if thesis_stage in LifecycleState.__members__:
        return LifecycleState[thesis_stage]

    if position.thesis.get("distribution_signal") or position.metadata.get("distribution_signal"):
        return LifecycleState.DISTRIBUTION

    if position.metadata.get("exit_signal") or position.thesis.get("exit_signal"):
        return LifecycleState.EXITING

    holding_days = float(position.metadata.get("holding_days", 0.0) or 0.0)
    if holding_days < 1.0:
        return LifecycleState.NEW
    if holding_days < 7.0:
        return LifecycleState.BUILDING
    if holding_days < 30.0:
        return LifecycleState.ACTIVE
    return LifecycleState.MATURE

"""System mode manager for manual/assisted/autonomous execution policies."""

from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Dict


@dataclass(frozen=True)
class ControlMode:
    MANUAL: str = "MANUAL"
    ASSISTED: str = "ASSISTED"
    AUTONOMOUS: str = "AUTONOMOUS"


class ModeManager:
    """Thread-safe mode state holder with policy checks."""

    def __init__(self, initial_mode: str = ControlMode.AUTONOMOUS):
        self._mode = str(initial_mode).strip().upper() or ControlMode.AUTONOMOUS
        self._lock = RLock()
        self._valid = {ControlMode.MANUAL, ControlMode.ASSISTED, ControlMode.AUTONOMOUS}

    def set_mode(self, mode: str) -> str:
        normalized = str(mode).strip().upper()
        if normalized not in self._valid:
            return f"Invalid mode: {mode}. Use MANUAL/ASSISTED/AUTONOMOUS."
        with self._lock:
            self._mode = normalized
        return f"Mode set to {normalized}."

    def get_mode(self) -> str:
        with self._lock:
            return self._mode

    def should_execute_autonomously(self) -> bool:
        return self.get_mode() == ControlMode.AUTONOMOUS

    def should_recommend_only(self) -> bool:
        return self.get_mode() == ControlMode.ASSISTED

    def should_block_trading(self) -> bool:
        return self.get_mode() == ControlMode.MANUAL

    def snapshot(self) -> Dict[str, str]:
        return {"mode": self.get_mode()}


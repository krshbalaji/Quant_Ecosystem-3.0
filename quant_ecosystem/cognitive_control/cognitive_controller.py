"""Cognitive controller coordinating monitor, memory, decisions, and behavior."""

from __future__ import annotations

import time
from typing import Dict, Optional

from quant_ecosystem.cognitive_control.behavior_manager import BehaviorManager
from quant_ecosystem.cognitive_control.cognitive_memory import CognitiveMemory
from quant_ecosystem.cognitive_control.decision_engine import DecisionEngine
from quant_ecosystem.cognitive_control.system_state_monitor import SystemStateMonitor


class CognitiveController:
    """Central cognitive control layer for adaptive system behavior."""

    def __init__(
        self,
        system_state_monitor: Optional[SystemStateMonitor] = None,
        decision_engine: Optional[DecisionEngine] = None,
        behavior_manager: Optional[BehaviorManager] = None,
        cognitive_memory: Optional[CognitiveMemory] = None,
    ):
        self.system_state_monitor = system_state_monitor or SystemStateMonitor()
        self.decision_engine = decision_engine or DecisionEngine()
        self.behavior_manager = behavior_manager or BehaviorManager()
        self.cognitive_memory = cognitive_memory or CognitiveMemory()
        self.last_decision: Dict = {}
        self._last_run_ts = 0.0

    def run_cycle(self, router, regime: str = "UNKNOWN") -> Dict:
        """Run one cognitive decision cycle and apply non-invasive behavior updates."""
        started = time.perf_counter()
        state = self.system_state_monitor.collect(router)
        state["regime"] = str(regime or "UNKNOWN").upper()
        self.cognitive_memory.append_state(state)
        summary = self.cognitive_memory.summary()
        decision = self.decision_engine.decide(state=state, memory_summary=summary)
        behavior = self.behavior_manager.apply(router=router, decision=decision)
        self.cognitive_memory.save()

        latency_ms = (time.perf_counter() - started) * 1000.0
        output = {
            "state": state,
            "decision": decision,
            "behavior": behavior,
            "memory": summary,
            "latency_ms": round(latency_ms, 3),
        }
        self.last_decision = output
        self._last_run_ts = time.time()
        return output

    def run_if_due(self, router, regime: str, interval_sec: float) -> Optional[Dict]:
        """Execute cycle if interval has elapsed; otherwise return None."""
        interval = max(0.5, float(interval_sec))
        now = time.time()
        if self._last_run_ts > 0.0 and (now - self._last_run_ts) < interval:
            return None
        return self.run_cycle(router=router, regime=regime)


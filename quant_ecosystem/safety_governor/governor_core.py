"""Safety Governor core orchestration."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from quant_ecosystem.safety_governor.execution_monitor import ExecutionMonitor
from quant_ecosystem.safety_governor.intervention_manager import InterventionManager
from quant_ecosystem.safety_governor.market_stress_monitor import MarketStressMonitor
from quant_ecosystem.safety_governor.risk_monitor import RiskMonitor
from quant_ecosystem.safety_governor.system_health_monitor import SystemHealthMonitor


class SafetyGovernor:
    """Central safety governor for trading/system/market interventions."""

    def __init__(
        self,
        risk_monitor: Optional[RiskMonitor] = None,
        execution_monitor: Optional[ExecutionMonitor] = None,
        system_health_monitor: Optional[SystemHealthMonitor] = None,
        market_stress_monitor: Optional[MarketStressMonitor] = None,
        intervention_manager: Optional[InterventionManager] = None,
    ):
        self.risk_monitor = risk_monitor or RiskMonitor()
        self.execution_monitor = execution_monitor or ExecutionMonitor()
        self.system_health_monitor = system_health_monitor or SystemHealthMonitor()
        self.market_stress_monitor = market_stress_monitor or MarketStressMonitor()
        self.intervention_manager = intervention_manager or InterventionManager()
        self.last_event: Dict = {}
        self.history: List[Dict] = []

    def monitor(self, router, context: Optional[Dict] = None) -> Dict:
        """Run all monitors, resolve severity, and apply safety intervention."""
        ctx = dict(context or {})
        alerts: List[Dict] = []
        alerts.extend(self.risk_monitor.evaluate(router=router, context=ctx))
        alerts.extend(self.execution_monitor.evaluate(router=router, context=ctx))
        alerts.extend(self.system_health_monitor.evaluate(router=router, context=ctx))
        alerts.extend(self.market_stress_monitor.evaluate(router=router, context=ctx))

        level = self.intervention_manager.resolve_level(alerts)
        if level == "NONE":
            event = {
                "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "alert_level": "NONE",
                "reason": "No abnormal conditions detected",
                "action": "NONE",
                "alerts": [],
            }
            self.last_event = event
            self._append(event)
            return event

        primary = self._pick_primary_reason(alerts, level)
        intervention = self.intervention_manager.apply(
            router=router,
            level=level,
            reason=primary.get("reason", "Safety rule triggered"),
            alerts=alerts,
        )
        event = {
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "alert_level": intervention.get("alert_level", level),
            "reason": intervention.get("reason", ""),
            "action": intervention.get("action", ""),
            "alerts": alerts,
        }
        self.last_event = event
        self._append(event)
        return event

    def _pick_primary_reason(self, alerts: List[Dict], level: str) -> Dict:
        lvl = str(level).upper()
        preferred = [item for item in alerts if str(item.get("level", "")).upper() == lvl]
        if preferred:
            return preferred[0]
        return alerts[0] if alerts else {"reason": "Unknown"}

    def _append(self, event: Dict) -> None:
        self.history = (self.history + [dict(event)])[-2000:]


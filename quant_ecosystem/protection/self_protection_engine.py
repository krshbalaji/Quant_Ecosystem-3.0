from quant_ecosystem.telemetry.nervous_system import (
    nervous_system,
)

from quant_ecosystem.protection.protection_state import (
    protection_state,
)


class SelfProtectionEngine:

    def evaluate(self):

        health = (
            nervous_system
            .current_health()
        )

        status = str(
            health.get(
                "status",
                "UNKNOWN",
            )
        ).upper()

        if status == "CRITICAL":

            protection_state.enable_emergency()

            protection_state.enable_degraded()

            protection_state.enable_throttle()

            return

        if status == "ELEVATED":

            protection_state.enable_throttle()

            protection_state.enable_degraded()

            return

        protection_state.disable_throttle()

        protection_state.disable_degraded()

        protection_state.disable_emergency()


self_protection_engine = (
    SelfProtectionEngine()
)
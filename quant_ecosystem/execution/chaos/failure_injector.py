from quant_ecosystem.execution.chaos.chaos_profiles import (
    ChaosProfile,
)


class FailureInjector:

    def __init__(self):
        self._profile = None
        self._enabled = False

    def enable(
        self,
        profile,
    ):
        self._profile = profile
        self._enabled = True

    def disable(self):
        self._profile = None
        self._enabled = False

    def inject(self):
        if not self._enabled:
            return

        if self._profile == ChaosProfile.TIMEOUT:
            raise TimeoutError(
                "Injected timeout failure"
            )

        if self._profile == ChaosProfile.DISCONNECT:
            raise ConnectionError(
                "Injected disconnect failure"
            )

        if self._profile == ChaosProfile.REJECT:
            raise RuntimeError(
                "Injected broker rejection"
            )

        if self._profile == ChaosProfile.MALFORMED_RESPONSE:
            return {
                "broken": True
            }

        if self._profile == ChaosProfile.FALSE_SUCCESS:
            return {
                "status": "SUCCESS",
                "order_id": None,
            }

        if self._profile == ChaosProfile.PARTIAL_FILL:
            return {
                "status": "PARTIAL",
                "filled_qty": 1,
            }
from quant_ecosystem.protection.protection_state import (
    protection_state,
)


class ThrottleGovernor:

    def scale_quantity(
        self,
        qty,
    ):

        if (
            protection_state
            .emergency()
        ):
            return max(
                1,
                int(qty * 0.10),
            )

        if (
            protection_state
            .degraded()
        ):
            return max(
                1,
                int(qty * 0.50),
            )

        if (
            protection_state
            .throttled()
        ):
            return max(
                1,
                int(qty * 0.75),
            )

        return qty


throttle_governor = (
    ThrottleGovernor()
)
from quant_ecosystem.execution.governance.order_lifecycle import (
    BLOCKED_MUTATION_STATES,
)


class MutationGuard:
    """
    Deterministic order mutation governance.
    """

    def ensure_mutable(
        self,
        lifecycle_state,
        operation,
    ):
        state = str(
            lifecycle_state or ""
        ).upper().strip()

        if state in BLOCKED_MUTATION_STATES:
            raise RuntimeError(
                f"{operation} BLOCKED: lifecycle={state}"
            )
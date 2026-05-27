from quant_ecosystem.execution.contracts.broker_response_validator import (
    BrokerResponseValidator,
)
from quant_ecosystem.execution.governance.execution_timeout_governor import (
    ExecutionTimeoutGovernor,
)


class LiveExecutionOrchestrator:

    def __init__(
        self,
        circuit_breaker,
        broker_health_router,
        notifier,
        failure_injector=None,
        response_validator=None,
        intent_journal=None,
        recovery_reconciler=None,
        broker_registry=None,
    ):
        self._circuit_breaker = circuit_breaker
        self._broker_health_router = broker_health_router
        self._notifier = notifier
        self._failure_injector = failure_injector
        self._response_validator = (
            response_validator
            or BrokerResponseValidator()
        )
        self._timeout_governor = (
            ExecutionTimeoutGovernor()
        )
        self._intent_journal = intent_journal
        self._recovery_reconciler = recovery_reconciler
        self._broker_registry = broker_registry

    def execute(
        self,
        broker,
        broker_name,
        normalized_symbol,
        symbol,
        side,
        qty,
        price,
        asset_class,
        execution_fn,
    ):
        started_at = (
            self._timeout_governor.start_deadline()
        )

        try:
            if self._failure_injector:
                injected = (
                    self._failure_injector.inject()
                )

                if injected is not None:
                    result = injected
                else:
                    result = execution_fn()
            else:
                result = execution_fn()

            result = self._response_validator.validate(
                result
            )

            self._broker_health_router.mark_healthy(
                broker_name
            )

            self._circuit_breaker.reset()

        except Exception as exc:
            self._broker_health_router.mark_unhealthy(
                broker_name
            )

            self._circuit_breaker.record_failure()

            if self._timeout_governor.expired(
                started_at
            ):
                if self._intent_journal:
                    intent_id = self._intent_journal.create_intent(
                        symbol=symbol,
                        side=side,
                        qty=qty,
                        price=price,
                        asset_class=asset_class,
                        broker_name=broker_name,
                        meta={
                            "reason": "timeout_uncertainty"
                        },
                        fingerprint="",
                    )

                    self._intent_journal.record_event(
                        intent_id=intent_id,
                        event="UNCERTAIN",
                    )

                    if (
                        self._recovery_reconciler
                        and
                        self._broker_registry
                    ):
                        recovered = (
                            self._recovery_reconciler.recover(
                                self._broker_registry
                            )
                        )

                        if recovered:
                            result = recovered[-1]
                            result["lifecycle_state"] = "FILLED"
                            return result

                raise RuntimeError(
                    f"STILL UNCERTAIN EXECUTION STATE: {broker_name}"
                ) from exc

            raise

        result = result or {}

        result.setdefault(
            "order_id",
            result.get("id", ""),
        )

        result.setdefault(
            "broker",
            getattr(
                broker,
                "account_source",
                type(broker).__name__.upper(),
            ),
        )

        result.setdefault(
            "execution_state",
            "CONFIRMED",
        )

        result.setdefault(
            "lifecycle_state",
            "FILLED",
        )

        return result
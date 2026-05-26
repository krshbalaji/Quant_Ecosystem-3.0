from quant_ecosystem.execution.contracts.broker_response_validator import (
    BrokerResponseValidator,
)

class LiveExecutionOrchestrator:

    def __init__(
        self,
        circuit_breaker,
        broker_health_router,
        notifier,
        failure_injector=None,
        response_validator=None,
    ):
        self._circuit_breaker = circuit_breaker
        self._broker_health_router = broker_health_router
        self._notifier = notifier
        self._failure_injector = failure_injector
        self._response_validator = (
            response_validator
            or BrokerResponseValidator()
        )

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

        return result
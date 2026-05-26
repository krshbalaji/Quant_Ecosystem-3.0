class CircuitBreakerGuard:

    def __init__(
        self,
        circuit_breaker,
    ):
        self._circuit_breaker = (
            circuit_breaker
        )

    def check(self):
        self._circuit_breaker.check()
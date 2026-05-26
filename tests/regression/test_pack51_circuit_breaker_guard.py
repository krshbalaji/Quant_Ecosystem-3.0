from quant_ecosystem.execution.guards.circuit_breaker_guard import (
    CircuitBreakerGuard,
)


class DummyBreaker:
    def __init__(self):
        self.called = False

    def check(self):
        self.called = True


def test_guard_calls_breaker():
    breaker = DummyBreaker()

    guard = CircuitBreakerGuard(
        breaker
    )

    guard.check()

    assert breaker.called is True
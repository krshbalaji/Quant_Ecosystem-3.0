import pytest

from quant_ecosystem.execution.chaos.failure_injector import (
    FailureInjector,
)

from quant_ecosystem.execution.chaos.chaos_profiles import (
    ChaosProfile,
)


def test_timeout_injection():
    injector = FailureInjector()

    injector.enable(
        ChaosProfile.TIMEOUT
    )

    with pytest.raises(TimeoutError):
        injector.inject()


def test_disconnect_injection():
    injector = FailureInjector()

    injector.enable(
        ChaosProfile.DISCONNECT
    )

    with pytest.raises(ConnectionError):
        injector.inject()


def test_malformed_response():
    injector = FailureInjector()

    injector.enable(
        ChaosProfile.MALFORMED_RESPONSE
    )

    result = injector.inject()

    assert result["broken"] is True


def test_disable():
    injector = FailureInjector()

    injector.enable(
        ChaosProfile.TIMEOUT
    )

    injector.disable()

    assert injector.inject() is None
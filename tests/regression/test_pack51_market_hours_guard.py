from quant_ecosystem.execution.guards.market_hours_guard import (
    MarketHoursGuard,
)


def test_market_open():
    guard = MarketHoursGuard()

    guard.check(
        strict_market_hours=True,
        market_open=True,
    )

    assert True


def test_market_closed():
    guard = MarketHoursGuard()

    try:
        guard.check(
            strict_market_hours=True,
            market_open=False,
        )
        assert False
    except RuntimeError:
        assert True


def test_disabled_guard():
    guard = MarketHoursGuard()

    guard.check(
        strict_market_hours=False,
        market_open=False,
    )

    assert True
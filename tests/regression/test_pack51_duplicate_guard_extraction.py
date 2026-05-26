from quant_ecosystem.execution.guards.duplicate_guard import (
    DuplicateOrderGuard,
)


def test_duplicate_block():
    guard = DuplicateOrderGuard()

    guard.check(
        symbol="INFY",
        side="BUY",
        qty=1,
    )

    try:
        guard.check(
            symbol="INFY",
            side="BUY",
            qty=1,
        )
        assert False
    except RuntimeError:
        assert True


def test_clear():
    guard = DuplicateOrderGuard()

    guard.check(
        symbol="INFY",
        side="BUY",
        qty=1,
    )

    guard.clear()

    guard.check(
        symbol="INFY",
        side="BUY",
        qty=1,
    )

    assert True
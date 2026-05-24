from quant_ecosystem.strategy import (
    capital_allocator,
)


def test_fixed_bucket():
    alloc = capital_allocator.fixed_bucket(
        100000,
        {
            "alpha": 0.50,
            "beta": 0.25,
        },
    )

    assert alloc["alpha"] == 50000
    assert alloc["beta"] == 25000


def test_proportional():
    alloc = capital_allocator.proportional_weights(
        100000,
        {
            "a": 2,
            "b": 1,
        },
    )

    assert alloc["a"] > alloc["b"]


def test_vol_targeted():
    alloc = capital_allocator.volatility_targeted(
        100000,
        {
            "low_vol": 0.10,
            "high_vol": 0.40,
        },
    )

    assert alloc["low_vol"] > alloc["high_vol"]


def test_drawdown_throttle():
    amt = capital_allocator.drawdown_throttle(
        100000,
        current_drawdown=0.15,
    )

    assert amt < 100000


def test_max_cap():
    capped = capital_allocator.enforce_max_cap(
        {
            "a": 80000,
            "b": 10000,
        },
        max_pct=0.40,
        total_capital=100000,
    )

    assert capped["a"] == 40000


def test_adaptive_rebalance():
    alloc = capital_allocator.adaptive_rebalance(
        total_capital=100000,
        strategy_scores={
            "a": 10,
            "b": 5,
        },
        drawdowns={
            "a": 0.20,
        },
        max_pct=0.50,
    )

    assert "a" in alloc
    assert "b" in alloc
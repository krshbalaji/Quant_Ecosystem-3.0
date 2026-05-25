from quant_ecosystem.portfolio.portfolio_optimizer import (
    portfolio_optimizer,
)


def test_equal_weight():
    result = (
        portfolio_optimizer
        .equal_weight(
            ["A", "B", "C"],
            300000,
        )
    )

    assert result["A"] == 100000
    assert result["B"] == 100000
    assert result["C"] == 100000


def test_target_weights():
    result = (
        portfolio_optimizer
        .target_weight_allocate(
            100000,
            {
                "A": 0.5,
                "B": 0.3,
                "C": 0.2,
            },
        )
    )

    assert result["A"] == 50000
    assert result["B"] == 30000
    assert result["C"] == 20000


def test_rebalance():
    result = (
        portfolio_optimizer
        .rebalance_orders(
            {
                "A": 40000,
                "B": 60000,
            },
            {
                "A": 50000,
                "B": 30000,
                "C": 20000,
            },
        )
    )

    assert result["A"] == 10000
    assert result["B"] == -30000
    assert result["C"] == 20000


def test_risk_parity():
    result = (
        portfolio_optimizer
        .risk_parity_allocate(
            100000,
            {
                "A": 0.10,
                "B": 0.20,
            },
        )
    )

    assert result["A"] > result["B"]


def test_efficiency():
    result = (
        portfolio_optimizer
        .capital_efficiency_score(
            expected_return=15,
            risk=5,
        )
    )

    assert result == 3.0
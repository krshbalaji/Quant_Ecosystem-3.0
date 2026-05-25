from quant_ecosystem.portfolio.stress_testing import (
    portfolio_stress_testing,
)


POSITIONS = [
    {
        "symbol": "SBIN",
        "market_value": 100000,
    },
    {
        "symbol": "INFY",
        "market_value": 50000,
    },
]

OPTION_POSITIONS = [
    {
        "symbol": "NIFTY_CE",
        "vega": 25,
        "qty": 10,
    }
]


def test_crash():
    result = (
        portfolio_stress_testing
        .crash_simulation(
            POSITIONS,
            -10,
        )
    )

    assert result == -15000


def test_vol_shock():
    result = (
        portfolio_stress_testing
        .volatility_shock(
            OPTION_POSITIONS,
            20,
        )
    )

    assert result == 50.0


def test_gap():
    result = (
        portfolio_stress_testing
        .gap_risk(
            POSITIONS,
            -5,
        )
    )

    assert result == -7500


def test_liquidity():
    result = (
        portfolio_stress_testing
        .liquidity_haircut(
            POSITIONS,
            10,
        )
    )

    assert (
        result[0]["stressed_value"]
        == 90000
    )


def test_scenario_matrix():
    result = (
        portfolio_stress_testing
        .scenario_matrix(
            POSITIONS
        )
    )

    assert "market_crash_10" in result
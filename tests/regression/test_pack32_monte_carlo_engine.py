from quant_ecosystem.backtest.monte_carlo_engine import (
    monte_carlo_engine,
)


PNL_SERIES = [
    100,
    -50,
    200,
    -100,
    75,
]


def test_shuffle():
    result = (
        monte_carlo_engine
        .shuffled_series(
            PNL_SERIES
        )
    )

    assert len(result) == 5


def test_drawdown():
    curve = [
        1000,
        1100,
        900,
        950,
    ]

    result = (
        monte_carlo_engine
        .max_drawdown(
            curve
        )
    )

    assert result == 200


def test_simulate():
    result = (
        monte_carlo_engine
        .simulate(
            PNL_SERIES,
            iterations=10,
        )
    )

    assert len(result) == 10


def test_run():
    result = (
        monte_carlo_engine
        .run(
            PNL_SERIES,
            iterations=10,
        )
    )

    assert (
        result["snapshot"]
        ["iterations"]
        == 10
    )
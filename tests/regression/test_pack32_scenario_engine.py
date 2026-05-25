from quant_ecosystem.backtest.scenario_engine import (
    scenario_engine,
)


PNL_SERIES = [
    100,
    -50,
    200,
    -100,
    75,
]


def test_crash():
    result = (
        scenario_engine
        .crash(PNL_SERIES)
    )

    assert result[0] == 50


def test_gap_down():
    result = (
        scenario_engine
        .gap_down(PNL_SERIES)
    )

    assert result[0] == 70
    assert result[1] < -50


def test_volatility_spike():
    result = (
        scenario_engine
        .volatility_spike(
            PNL_SERIES
        )
    )

    assert result[0] == 150


def test_run():
    result = (
        scenario_engine
        .run(PNL_SERIES)
    )

    assert "crash" in result
    assert "gap_down" in result
    assert "gap_up" in result
    assert (
        "volatility_spike"
        in result
    )
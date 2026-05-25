from quant_ecosystem.research.technical_signal_engine import (
    technical_signal_engine,
)


SERIES = list(range(100, 140))


def test_sma_signal():
    result = (
        technical_signal_engine
        .sma_crossover(
            "SBIN",
            SERIES,
        )
    )

    assert result.signal_type == (
        "SMA_CROSSOVER"
    )


def test_ema_signal():
    result = (
        technical_signal_engine
        .ema_trend(
            "SBIN",
            SERIES,
        )
    )

    assert result.signal_type == (
        "EMA_TREND"
    )


def test_breakout():
    result = (
        technical_signal_engine
        .breakout(
            "SBIN",
            SERIES,
        )
    )

    assert result.signal_type == (
        "BREAKOUT"
    )


def test_momentum():
    result = (
        technical_signal_engine
        .momentum(
            "SBIN",
            SERIES,
        )
    )

    assert result.signal_type == (
        "MOMENTUM"
    )


def test_mean_reversion():
    result = (
        technical_signal_engine
        .mean_reversion(
            "SBIN",
            SERIES,
        )
    )

    assert result.signal_type == (
        "MEAN_REVERSION"
    )
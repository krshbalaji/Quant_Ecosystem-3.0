from quant_ecosystem.research.regime_detection_engine import (
    regime_detection_engine,
)


TREND_SERIES = [
    100,
    102,
    104,
    106,
    108,
    110,
    112,
    114,
    116,
    118,
    120,
    122,
    124,
    126,
    128,
    130,
    132,
    134,
    136,
    138,
    140,
]

MEANREV_SERIES = [
    100,
    101,
    99,
    100,
    101,
    99,
    100,
    101,
    99,
    100,
    101,
    99,
    100,
    101,
    99,
    100,
    101,
    99,
    100,
    101,
    99,
]


def test_trend_detection():
    result = (
        regime_detection_engine
        .trend_regime(
            TREND_SERIES
        )
    )

    assert result == "TRENDING"


def test_meanrev_detection():
    result = (
        regime_detection_engine
        .trend_regime(
            MEANREV_SERIES
        )
    )

    assert result == (
        "MEAN_REVERTING"
    )


def test_vol_regime():
    result = (
        regime_detection_engine
        .volatility_regime(
            TREND_SERIES
        )
    )

    assert result in [
        "VOLATILE",
        "LOW_VOL",
    ]


def test_detect():
    result = (
        regime_detection_engine
        .detect(
            TREND_SERIES
        )
    )

    assert "regime" in result
    assert "confidence" in result
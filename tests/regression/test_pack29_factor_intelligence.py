from quant_ecosystem.portfolio.factor_intelligence import (
    portfolio_factor_intelligence,
)


SERIES_A = [
    100,
    102,
    104,
    106,
    108,
    110,
]

SERIES_B = [
    200,
    204,
    208,
    212,
    216,
    220,
]

SERIES_C = [
    100,
    99,
    101,
    98,
    100,
    97,
]


def test_volatility():
    result = (
        portfolio_factor_intelligence
        .rolling_volatility(SERIES_A)
    )

    assert result >= 0.0


def test_beta():
    result = (
        portfolio_factor_intelligence
        .beta(
            SERIES_A,
            SERIES_B,
        )
    )

    assert result > 0.0


def test_momentum():
    result = (
        portfolio_factor_intelligence
        .momentum(
            SERIES_A,
            lookback=3,
        )
    )

    assert result > 0.0


def test_correlation():
    result = (
        portfolio_factor_intelligence
        .rolling_correlation(
            SERIES_A,
            SERIES_B,
        )
    )

    assert result > 0.9


def test_clusters():
    result = (
        portfolio_factor_intelligence
        .correlation_clusters(
            {
                "A": SERIES_A,
                "B": SERIES_B,
                "C": SERIES_C,
            }
        )
    )

    assert len(result) >= 1
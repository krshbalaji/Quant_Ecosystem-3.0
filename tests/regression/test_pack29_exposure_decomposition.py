from quant_ecosystem.portfolio.exposure_decomposition import (
    portfolio_exposure_decomposition,
)


POSITIONS = [
    {
        "symbol": "SBIN",
        "market_value": 100000,
        "asset_class": "EQUITY",
        "qty": 100,
        "delta": 1.0,
    },
    {
        "symbol": "NIFTY_CE",
        "market_value": 50000,
        "asset_class": "OPTION",
        "qty": 50,
        "delta": 0.5,
    },
    {
        "symbol": "BANKNIFTY_PE",
        "market_value": -25000,
        "asset_class": "OPTION",
        "qty": -25,
        "delta": -0.4,
    },
]


def test_gross_exposure():
    result = (
        portfolio_exposure_decomposition
        .gross_exposure(POSITIONS)
    )

    assert result == 175000


def test_net_exposure():
    result = (
        portfolio_exposure_decomposition
        .net_exposure(POSITIONS)
    )

    assert result == 125000


def test_asset_breakdown():
    result = (
        portfolio_exposure_decomposition
        .asset_class_breakdown(POSITIONS)
    )

    assert result["EQUITY"] == 100000
    assert result["OPTION"] == 75000


def test_directional_delta():
    result = (
        portfolio_exposure_decomposition
        .directional_delta(POSITIONS)
    )

    assert result == 135.0


def test_summary():
    result = (
        portfolio_exposure_decomposition
        .exposure_summary(POSITIONS)
    )

    assert result["gross_exposure"] == 175000
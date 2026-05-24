from quant_ecosystem.market.options.volatility_engine import (
    volatility_engine,
)


def test_log_returns():
    prices = [100, 101, 102]

    r = volatility_engine.log_returns(prices)

    assert len(r) == 2


def test_historical_volatility():
    prices = [
        100, 102, 101, 104,
        103, 106, 108
    ]

    hv = volatility_engine.historical_volatility(
        prices
    )

    assert hv > 0


def test_realized_volatility():
    rv = volatility_engine.realized_volatility(
        [0.01, -0.02, 0.015]
    )

    assert rv > 0


def test_iv_percentile():
    pct = volatility_engine.iv_percentile(
        0.25,
        [0.10, 0.15, 0.20, 0.30, 0.40],
    )

    assert pct > 0


def test_volatility_regimes():
    assert (
        volatility_engine.volatility_regime(0.10)
        == "LOW"
    )

    assert (
        volatility_engine.volatility_regime(0.20)
        == "NORMAL"
    )

    assert (
        volatility_engine.volatility_regime(0.40)
        == "HIGH"
    )


def test_iv_solver():
    target_price = 10.0

    def pricing_fn(vol):
        mock_price = vol * 50
        mock_vega = 50
        return mock_price, mock_vega

    iv = volatility_engine.implied_volatility(
        market_price=target_price,
        pricing_function=pricing_fn,
    )

    assert abs(iv - 0.20) < 0.01
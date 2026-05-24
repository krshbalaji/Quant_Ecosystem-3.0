from quant_ecosystem.market.options.greeks_engine import (
    greeks_engine,
)


def test_call_delta_positive():
    g = greeks_engine.calculate(
        spot=24500,
        strike=24500,
        rate=0.05,
        volatility=0.20,
        time_to_expiry=0.08,
        option_type="CE",
    )

    assert g.delta > 0
    assert g.gamma > 0
    assert g.vega > 0


def test_put_delta_negative():
    g = greeks_engine.calculate(
        spot=24500,
        strike=24500,
        rate=0.05,
        volatility=0.20,
        time_to_expiry=0.08,
        option_type="PE",
    )

    assert g.delta < 0


def test_invalid_inputs_safe():
    g = greeks_engine.calculate(
        spot=0,
        strike=24500,
        rate=0.05,
        volatility=0.20,
        time_to_expiry=0.08,
        option_type="CE",
    )

    assert g.delta == 0.0
    assert g.gamma == 0.0
from quant_ecosystem.strategy import (
    exposure_governor,
)


def test_symbol_overlap():
    signals = [
        {
            "symbol": "NIFTY",
            "side": "BUY",
        },
        {
            "symbol": "NIFTY",
            "side": "SELL",
        },
    ]

    overlaps = exposure_governor.symbol_overlap(
        signals
    )

    assert "NIFTY" in overlaps


def test_directional_conflict():
    signals = [
        {
            "symbol": "NIFTY",
            "side": "BUY",
        },
        {
            "symbol": "NIFTY",
            "side": "SELL",
        },
    ]

    conflicts = exposure_governor.directional_conflicts(
        signals
    )

    assert "NIFTY" in conflicts


def test_concentration():
    breaches = exposure_governor.concentration_check(
        {
            "alpha": 60000,
            "beta": 20000,
        },
        max_pct=0.40,
        total_capital=100000,
    )

    assert "alpha" in breaches


def test_gross_exposure():
    gross = exposure_governor.gross_exposure(
        [
            {
                "qty": 10,
                "price": 100,
            },
            {
                "qty": 5,
                "price": 200,
            },
        ]
    )

    assert gross == 2000


def test_hedge_recognition():
    result = exposure_governor.hedge_recognition(
        [
            {
                "symbol": "NIFTY",
                "trade_type": "HEDGE",
            },
            {
                "symbol": "SBIN",
            },
        ]
    )

    assert len(result["hedges"]) == 1
    assert len(result["directional"]) == 1


def test_correlated_overlap():
    result = exposure_governor.correlated_overlap(
        [
            {"symbol": "NIFTY"},
            {"symbol": "BANKNIFTY"},
        ],
        {
            "INDEX": [
                "NIFTY",
                "BANKNIFTY",
            ]
        },
    )

    assert "INDEX" in result
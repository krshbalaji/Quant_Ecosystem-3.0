from quant_ecosystem.strategy import (
    signal_arbitrator,
)


def test_priority_resolution():
    signals = [
        {
            "symbol": "NIFTY",
            "side": "BUY",
            "priority": 50,
        },
        {
            "symbol": "NIFTY",
            "side": "SELL",
            "priority": 10,
        },
    ]

    result = signal_arbitrator.priority_resolution(
        signals
    )

    assert len(result) == 1
    assert result[0]["side"] == "SELL"


def test_confidence_weighted():
    signals = [
        {
            "symbol": "NIFTY",
            "side": "BUY",
            "confidence": 0.8,
        },
        {
            "symbol": "NIFTY",
            "side": "SELL",
            "confidence": 0.2,
        },
    ]

    result = signal_arbitrator.confidence_weighted(
        signals
    )

    assert result[0]["side"] == "BUY"


def test_consensus():
    signals = [
        {
            "symbol": "NIFTY",
            "side": "BUY",
        },
        {
            "symbol": "NIFTY",
            "side": "BUY",
        },
    ]

    result = signal_arbitrator.consensus(
        signals
    )

    assert len(result) == 1


def test_veto():
    signals = [
        {
            "symbol": "NIFTY",
            "side": "BUY",
            "veto": True,
        }
    ]

    result = signal_arbitrator.veto(
        signals
    )

    assert result == []


def test_hedge_aware():
    signals = [
        {
            "symbol": "NIFTY",
            "side": "BUY",
            "priority": 10,
        },
        {
            "symbol": "NIFTYPUT",
            "side": "BUY",
            "trade_type": "HEDGE",
        },
    ]

    result = signal_arbitrator.hedge_aware(
        signals
    )

    assert len(result) == 2
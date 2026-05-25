from quant_ecosystem.research import (
    AlphaSignal,
)

from quant_ecosystem.research.alpha_scoring_engine import (
    alpha_scoring_engine,
)


def test_conviction_weight():
    result = (
        alpha_scoring_engine
        .conviction_weight(85)
    )

    assert result == 1.25


def test_regime_multiplier():
    result = (
        alpha_scoring_engine
        .regime_multiplier(
            "TREND_VOL"
        )
    )

    assert result == 1.20


def test_alpha_score():
    signal = AlphaSignal(
        symbol="SBIN",
        direction="LONG",
        confidence=80,
    )

    result = (
        alpha_scoring_engine
        .alpha_score(
            signal,
            "TREND_LOWVOL",
        )
    )

    assert result > 80


def test_rank():
    signals = [
        AlphaSignal(
            symbol="SBIN",
            direction="LONG",
            confidence=85,
        ),
        AlphaSignal(
            symbol="INFY",
            direction="LONG",
            confidence=60,
        ),
    ]

    ranked = (
        alpha_scoring_engine
        .rank(
            signals,
            regime="TREND_VOL",
        )
    )

    assert ranked[0].symbol == "SBIN"
    assert ranked[0].rank == 1


def test_shortlist():
    signals = [
        AlphaSignal(
            symbol="A",
            direction="LONG",
            confidence=90,
        ),
        AlphaSignal(
            symbol="B",
            direction="LONG",
            confidence=80,
        ),
        AlphaSignal(
            symbol="C",
            direction="LONG",
            confidence=70,
        ),
    ]

    ranked = (
        alpha_scoring_engine
        .rank(signals)
    )

    shortlist = (
        alpha_scoring_engine
        .shortlist(
            ranked,
            top_n=2,
        )
    )

    assert len(shortlist) == 2
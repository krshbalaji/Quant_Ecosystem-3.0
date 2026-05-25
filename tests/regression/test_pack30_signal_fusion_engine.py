from quant_ecosystem.research import (
    TechnicalSignal,
    FactorSignal,
)

from quant_ecosystem.research.signal_fusion_engine import (
    signal_fusion_engine,
)


def test_direction_resolution():
    signals = [
        TechnicalSignal(
            symbol="SBIN",
            signal_type="BREAKOUT",
            direction="LONG",
            confidence=80,
        ),
        TechnicalSignal(
            symbol="SBIN",
            signal_type="TREND",
            direction="SHORT",
            confidence=30,
        ),
    ]

    result = (
        signal_fusion_engine
        .resolve_direction(
            signals
        )
    )

    assert result == "LONG"


def test_confidence_fusion():
    signals = [
        TechnicalSignal(
            symbol="SBIN",
            signal_type="BREAKOUT",
            direction="LONG",
            confidence=80,
        ),
        FactorSignal(
            symbol="SBIN",
            factor_name="MOMENTUM",
            score=1.2,
            confidence=60,
        ),
    ]

    result = (
        signal_fusion_engine
        .fused_confidence(
            signals
        )
    )

    assert result == 70


def test_alpha_fusion():
    signals = [
        TechnicalSignal(
            symbol="SBIN",
            signal_type="BREAKOUT",
            direction="LONG",
            confidence=80,
        ),
        TechnicalSignal(
            symbol="SBIN",
            signal_type="EMA",
            direction="LONG",
            confidence=75,
        ),
    ]

    alpha = (
        signal_fusion_engine
        .fuse(
            "SBIN",
            signals,
        )
    )

    assert alpha.direction == "LONG"
    assert alpha.metadata["signal_count"] == 2


def test_ranking():
    alpha_signals = [
        signal_fusion_engine.fuse(
            "SBIN",
            [
                TechnicalSignal(
                    symbol="SBIN",
                    signal_type="X",
                    direction="LONG",
                    confidence=90,
                )
            ],
        ),
        signal_fusion_engine.fuse(
            "INFY",
            [
                TechnicalSignal(
                    symbol="INFY",
                    signal_type="X",
                    direction="LONG",
                    confidence=60,
                )
            ],
        ),
    ]

    ranked = (
        signal_fusion_engine
        .rank_opportunities(
            alpha_signals
        )
    )

    assert ranked[0].symbol == "SBIN"
    assert ranked[0].rank == 1
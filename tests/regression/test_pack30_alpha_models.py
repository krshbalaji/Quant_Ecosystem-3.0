from quant_ecosystem.research import (
    ResearchHypothesis,
    TechnicalSignal,
    FactorSignal,
    AlphaSignal,
    RankedOpportunity,
    signal_confidence_engine,
)


def test_models():
    h = ResearchHypothesis(
        hypothesis_id="H1",
        title="Trend thesis",
        thesis="Momentum continuation",
    )

    s = TechnicalSignal(
        symbol="SBIN",
        signal_type="BREAKOUT",
        direction="LONG",
        confidence=75,
    )

    f = FactorSignal(
        symbol="SBIN",
        factor_name="MOMENTUM",
        score=1.2,
        confidence=70,
    )

    a = AlphaSignal(
        symbol="SBIN",
        direction="LONG",
        confidence=80,
    )

    r = RankedOpportunity(
        symbol="SBIN",
        alpha_score=92,
        confidence=85,
    )

    assert h.hypothesis_id == "H1"
    assert s.direction == "LONG"
    assert f.factor_name == "MOMENTUM"
    assert a.confidence == 80
    assert r.alpha_score == 92


def test_confidence_engine():
    score = (
        signal_confidence_engine
        .weighted_confidence(
            [
                (80, 0.5),
                (60, 0.5),
            ]
        )
    )

    assert score == 70

    assert (
        signal_confidence_engine
        .conviction(85)
        == "HIGH"
    )
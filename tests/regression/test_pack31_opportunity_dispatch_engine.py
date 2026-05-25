from quant_ecosystem.research import (
    RankedOpportunity,
)

from quant_ecosystem.research.opportunity_dispatch_engine import (
    opportunity_dispatch_engine,
)


def sample_ranked():
    return [
        RankedOpportunity(
            symbol="SBIN",
            alpha_score=95,
            confidence=90,
            rank=1,
            metadata={
                "direction": "LONG"
            },
        ),
        RankedOpportunity(
            symbol="INFY",
            alpha_score=80,
            confidence=70,
            rank=2,
            metadata={
                "direction": "SHORT"
            },
        ),
        RankedOpportunity(
            symbol="TCS",
            alpha_score=60,
            confidence=55,
            rank=3,
            metadata={
                "direction": "LONG"
            },
        ),
    ]


def test_top_opportunities():
    result = (
        opportunity_dispatch_engine
        .top_opportunities(
            sample_ranked(),
            top_n=2,
        )
    )

    assert len(result) == 2
    assert result[0].symbol == "SBIN"


def test_execution_candidates():
    result = (
        opportunity_dispatch_engine
        .execution_candidates(
            sample_ranked(),
        )
    )

    assert len(result) == 3
    assert result[0].strategy_id == (
        "alpha_SBIN"
    )


def test_alert_payload():
    result = (
        opportunity_dispatch_engine
        .alert_payload(
            sample_ranked()[0]
        )
    )

    assert result["symbol"] == "SBIN"
    assert result["rank"] == 1


def test_dispatch():
    result = (
        opportunity_dispatch_engine
        .dispatch(
            sample_ranked(),
            top_n=2,
        )
    )

    assert len(
        result["selected"]
    ) == 2

    assert len(
        result["execution_candidates"]
    ) == 2

    assert len(
        result["alerts"]
    ) == 2
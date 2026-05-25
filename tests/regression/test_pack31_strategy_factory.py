from quant_ecosystem.research import (
    RankedOpportunity,
)

from quant_ecosystem.research.strategy_factory import (
    strategy_factory,
)


def test_create_intent():
    opportunity = RankedOpportunity(
        symbol="SBIN",
        alpha_score=95,
        confidence=88,
        rank=1,
        metadata={
            "direction": "LONG"
        },
    )

    intent = (
        strategy_factory
        .create_intent(
            opportunity
        )
    )

    assert intent.strategy_id == (
        "alpha_SBIN"
    )
    assert intent.side == "BUY"


def test_create_risk_budget():
    opportunity = RankedOpportunity(
        symbol="INFY",
        alpha_score=80,
        confidence=70,
    )

    budget = (
        strategy_factory
        .create_risk_budget(
            opportunity
        )
    )

    assert budget.strategy_id == (
        "alpha_INFY"
    )
    assert budget.max_capital == 100000


def test_batch_create():
    opportunities = [
        RankedOpportunity(
            symbol="SBIN",
            alpha_score=95,
            confidence=88,
            metadata={
                "direction": "LONG"
            },
        ),
        RankedOpportunity(
            symbol="INFY",
            alpha_score=80,
            confidence=72,
            metadata={
                "direction": "SHORT"
            },
        ),
    ]

    intents = (
        strategy_factory
        .batch_create(
            opportunities
        )
    )

    assert len(intents) == 2
    assert intents[0].side == "BUY"
    assert intents[1].side == "SELL"
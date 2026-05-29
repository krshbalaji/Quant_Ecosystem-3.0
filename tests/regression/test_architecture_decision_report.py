from quant_ecosystem.cognition.swarm import (
    ArchitectureDecisionReport,
)


def test_decision_report():

    report = (
        ArchitectureDecisionReport(
            recommended_category="governance",
            priority_score=9.0,
        )
    )

    assert report.priority_score == 9.0
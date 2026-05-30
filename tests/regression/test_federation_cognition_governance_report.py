from quant_ecosystem.cognition.swarm import (
    FederationCognitionGovernanceReport,
)


def test_governance_report():

    report = (
        FederationCognitionGovernanceReport(
            governance_action="REVIEW",
            review_required=True,
        )
    )

    assert report.review_required is True
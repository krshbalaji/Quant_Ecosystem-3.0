from quant_ecosystem.cognition.swarm import (
    FederationCognitionWorkflowResult,
    FederationCognitionGovernanceAdapter,
)


def test_governance_adapter():

    result = (
        FederationCognitionWorkflowResult(
            workflow_name="wf",
            accepted=True,
        )
    )

    report = (
        FederationCognitionGovernanceAdapter()
        .adapt(result)
    )

    assert report.review_required is True

    assert (
        report.governance_action
        == "AUTHORIZE_EXECUTION_REVIEW"
    )
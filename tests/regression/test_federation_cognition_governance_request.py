from quant_ecosystem.cognition.swarm import (
    FederationCognitionGovernanceRequest,
)


def test_governance_request():

    request = (
        FederationCognitionGovernanceRequest(
            recommended_action="ACT",
            source_workflow="wf",
        )
    )

    assert request.source_workflow == "wf"
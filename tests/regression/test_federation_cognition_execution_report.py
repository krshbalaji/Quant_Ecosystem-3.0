from quant_ecosystem.cognition.swarm import (
    FederationCognitionExecutionReport,
)


def test_execution_report():

    report = (
        FederationCognitionExecutionReport(
            workflow_name="wf",
            action="ACT",
            execution_ready=True,
        )
    )

    assert report.execution_ready is True
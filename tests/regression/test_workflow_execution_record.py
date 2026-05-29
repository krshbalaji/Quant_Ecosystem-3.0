from quant_ecosystem.cognition.swarm import (
    WorkflowExecutionRecord,
)


def test_record_model():

    record = WorkflowExecutionRecord(
        workflow_id="WF1",
        successful=True,
        stage_results=[],
    )

    assert record.successful
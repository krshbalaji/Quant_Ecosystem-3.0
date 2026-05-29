from quant_ecosystem.cognition.swarm import (
    WorkflowExecutionSummary,
)


def test_summary_model():

    summary = (
        WorkflowExecutionSummary(
            total_steps=3,
            completed_steps=3,
            successful=True,
        )
    )

    assert summary.successful
from quant_ecosystem.cognition.swarm import (
    ExecutionFeedback,
)


def test_execution_feedback():

    feedback = (
        ExecutionFeedback(
            execution_id="E1",
            successful=True,
            stages_completed=3,
        )
    )

    assert feedback.successful
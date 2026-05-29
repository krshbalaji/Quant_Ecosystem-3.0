from quant_ecosystem.cognition.swarm import (
    ExecutionFeedback,
    FeedbackObservationAdapter,
)


def test_feedback_adapter():

    feedback = ExecutionFeedback(
        execution_id="E1",
        successful=True,
        stages_completed=2,
    )

    observation = (
        FeedbackObservationAdapter()
        .adapt(feedback)
    )

    assert observation.category == "success"
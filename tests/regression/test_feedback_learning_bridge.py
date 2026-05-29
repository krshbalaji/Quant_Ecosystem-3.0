from quant_ecosystem.cognition.swarm import (
    ExecutionFeedback,
    FeedbackLearningBridge,
)


def test_feedback_learning_bridge():

    result = (
        FeedbackLearningBridge()
        .learn(
            [
                ExecutionFeedback(
                    execution_id="E1",
                    successful=True,
                    stages_completed=1,
                ),
                ExecutionFeedback(
                    execution_id="E2",
                    successful=False,
                    stages_completed=1,
                ),
            ]
        )
    )

    assert result.pattern_count == 2
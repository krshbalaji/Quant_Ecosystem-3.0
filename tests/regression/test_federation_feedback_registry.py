from quant_ecosystem.cognition.swarm import (
    ExecutionFeedback,
    FederationFeedbackRegistry,
)


def test_feedback_registry():

    registry = (
        FederationFeedbackRegistry()
    )

    registry.register(
        ExecutionFeedback(
            execution_id="E1",
            successful=True,
            stages_completed=2,
        )
    )

    assert registry.count() == 1
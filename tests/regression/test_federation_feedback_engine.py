from quant_ecosystem.cognition.swarm import (
    ExecutionFeedback,
    FederationFeedbackEngine,
    FederationFeedbackRegistry,
)


def test_feedback_engine():

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

    registry.register(
        ExecutionFeedback(
            execution_id="E2",
            successful=False,
            stages_completed=1,
        )
    )

    report = (
        FederationFeedbackEngine()
        .evaluate(
            registry
        )
    )

    assert report.total_executions == 2
    assert report.successful_executions == 1
    assert report.success_rate == 0.5
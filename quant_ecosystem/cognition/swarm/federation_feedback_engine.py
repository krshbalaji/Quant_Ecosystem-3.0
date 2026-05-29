from .execution_feedback_report import (
    ExecutionFeedbackReport,
)
from .federation_feedback_registry import (
    FederationFeedbackRegistry,
)


class FederationFeedbackEngine:

    def evaluate(
        self,
        registry: FederationFeedbackRegistry,
    ) -> ExecutionFeedbackReport:

        entries = registry.feedback()

        if not entries:

            return (
                ExecutionFeedbackReport(
                    total_executions=0,
                    successful_executions=0,
                    success_rate=0.0,
                )
            )

        successful = sum(
            1
            for item in entries
            if item.successful
        )

        return (
            ExecutionFeedbackReport(
                total_executions=len(
                    entries
                ),
                successful_executions=(
                    successful
                ),
                success_rate=(
                    successful
                    / len(entries)
                ),
            )
        )
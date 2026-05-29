from .collective_learning_engine import (
    CollectiveLearningEngine,
)
from .feedback_learning_result import (
    FeedbackLearningResult,
)
from .feedback_observation_adapter import (
    FeedbackObservationAdapter,
)
from .execution_feedback import (
    ExecutionFeedback,
)


class FeedbackLearningBridge:

    def learn(
        self,
        feedback_items,
    ) -> FeedbackLearningResult:

        observations = [
            FeedbackObservationAdapter()
            .adapt(item)
            for item in feedback_items
        ]

        patterns = (
            CollectiveLearningEngine()
            .discover_patterns(
                observations
            )
        )

        return FeedbackLearningResult(
            pattern_count=len(
                patterns
            )
        )
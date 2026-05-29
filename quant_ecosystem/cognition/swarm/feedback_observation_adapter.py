from .execution_feedback import (
    ExecutionFeedback,
)
from .federation_observation import (
    FederationObservation,
)


class FeedbackObservationAdapter:

    def adapt(
        self,
        feedback: ExecutionFeedback,
    ) -> FederationObservation:

        category = (
            "success"
            if feedback.successful
            else "failure"
        )

        return FederationObservation(
            organism_id="feedback",
            category=category,
            observation_id=(
                feedback.execution_id
            ),
            payload={
                "successful": (
                    feedback.successful
                ),
                "stages_completed": (
                    feedback.stages_completed
                ),
            },
        )
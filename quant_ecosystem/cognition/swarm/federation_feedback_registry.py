from quant_ecosystem.core.append_registry import (
    AppendRegistry,
)

from .execution_feedback import (
    ExecutionFeedback,
)


class FederationFeedbackRegistry(
    AppendRegistry[
        ExecutionFeedback
    ]
):

    def feedback(
        self,
    ) -> list[ExecutionFeedback]:

        return self.entries()
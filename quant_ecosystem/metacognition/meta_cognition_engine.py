from quant_ecosystem.metacognition.execution_rationale import (
    ExecutionRationale,
)

from quant_ecosystem.metacognition.reasoning_memory import (
    reasoning_memory,
)


class MetaCognitionEngine:

    def reflect(
        self,
        *,
        broker,
        regime,
        aggression,
        consensus_approved,
        shard_id,
    ):

        explanation = (
            f"Executed via {broker} "
            f"under regime {regime} "
            f"with aggression {aggression}"
        )

        rationale = (
            ExecutionRationale(
                broker=broker,
                regime=regime,
                aggression=aggression,
                consensus_approved=(
                    consensus_approved
                ),
                shard_id=shard_id,
                explanation=(
                    explanation
                ),
            )
        )

        reasoning_memory.record(
            rationale
        )

    def latest_reasoning(self):

        rationale = (
            reasoning_memory.latest()
        )

        if rationale is None:

            return (
                "No reasoning available"
            )

        return rationale.explanation


meta_cognition_engine = (
    MetaCognitionEngine()
)
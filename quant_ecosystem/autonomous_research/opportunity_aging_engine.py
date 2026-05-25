from quant_ecosystem.autonomous_research.signal_decay_engine import (
    signal_decay_engine,
)


class OpportunityAgingEngine:

    def evaluate(
        self,
        confidence,
        age_hours,
    ):
        current = (
            signal_decay_engine
            .confidence_decay(
                confidence,
                age_hours,
            )
        )

        status = (
            signal_decay_engine
            .classify(current)
        )

        return {
            "confidence": current,
            "status": status,
            "retire": status == "EXPIRED",
        }


opportunity_aging_engine = (
    OpportunityAgingEngine()
)
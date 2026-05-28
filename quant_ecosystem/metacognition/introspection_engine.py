from quant_ecosystem.metacognition.meta_cognition_engine import (
    meta_cognition_engine,
)


class IntrospectionEngine:

    def summarize(self):

        return (
            meta_cognition_engine
            .latest_reasoning()
        )


introspection_engine = (
    IntrospectionEngine()
)
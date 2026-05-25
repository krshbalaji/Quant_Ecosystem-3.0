from quant_ecosystem.workflow import (
    workflow_engine,
)


class OrchestrationEndpoint:

    def execute(
        self,
        steps,
    ):
        return workflow_engine.execute(
            steps
        )


orchestration_endpoint = (
    OrchestrationEndpoint()
)
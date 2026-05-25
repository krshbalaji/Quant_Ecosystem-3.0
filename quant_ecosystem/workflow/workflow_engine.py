from quant_ecosystem.workflow.step_runner import (
    step_runner,
)

from quant_ecosystem.workflow.compensation_engine import (
    compensation_engine,
)


class WorkflowEngine:

    def execute(
        self,
        steps,
        compensations=None,
    ):
        results = []

        try:
            for step in steps:
                results.append(
                    step_runner.run(step)
                )

            return {
                "success": True,
                "results": results,
            }

        except Exception:
            if compensations:
                compensation_engine.compensate(
                    compensations
                )

            return {
                "success": False,
                "results": results,
            }


workflow_engine = WorkflowEngine()
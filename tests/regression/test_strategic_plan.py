from quant_ecosystem.cognition.swarm import (
    StrategicPlan,
)


def test_strategic_plan():

    plan = StrategicPlan(
        objective_count=0,
        objectives=[],
    )

    assert plan.objective_count == 0
from quant_ecosystem.cognition.swarm import (
    ImprovementCandidate,
)


def test_improvement_candidate():

    candidate = (
        ImprovementCandidate(
            category_name="execution",
            improvement_score=8.0,
        )
    )

    assert (
        candidate.improvement_score
        == 8.0
    )
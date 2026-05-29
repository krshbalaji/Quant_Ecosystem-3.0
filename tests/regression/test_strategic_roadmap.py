from quant_ecosystem.cognition.swarm import (
    StrategicRoadmap,
)


def test_roadmap_model():

    roadmap = StrategicRoadmap(
        roadmap_steps=[]
    )

    assert len(
        roadmap.roadmap_steps
    ) == 0
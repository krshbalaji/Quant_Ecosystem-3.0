from quant_ecosystem.cognition.swarm import (
    ExecutionLineage,
    FederationAuditRegistry,
)


def test_registry_tracks_lineage():

    registry = FederationAuditRegistry()

    lineage = ExecutionLineage(
        lineage_id="L1"
    )

    registry.register(lineage)

    assert registry.exists("L1")
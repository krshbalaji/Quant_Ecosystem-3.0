from quant_ecosystem.cognition.swarm import (
    TopologyAuditResult,
)


def test_topology_audit_result():

    result = TopologyAuditResult(
        total_symbols=10,
        duplicate_symbols=2,
    )

    assert result.total_symbols == 10
    assert result.duplicate_symbols == 2
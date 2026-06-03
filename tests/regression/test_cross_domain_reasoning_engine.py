from quant_ecosystem.cognition.swarm import (
    CrossDomainReasoningEngine,
    KnowledgeGraphEngine,
    KnowledgePattern,
    KnowledgeRegistry,
)


def test_cross_domain_reasoning_engine_generates_deterministic_chains():
    registry = KnowledgeRegistry()
    root = KnowledgePattern(
        category="DATA",
        frequency=1,
        pattern_id="knowledge.ROOT",
        source_keys=("audit.execution.lineage.L-100",),
        provenance=(),
    )
    child = KnowledgePattern(
        category="ANALYTICS",
        frequency=1,
        pattern_id="knowledge.CHILD",
        source_keys=("audit.execution.lineage.L-101",),
        provenance=("knowledge.ROOT",),
    )

    registry.register(root)
    registry.register(child)

    graph = KnowledgeGraphEngine().build_graph(registry)
    engine = CrossDomainReasoningEngine()

    first_result = engine.reason(graph, registry, "knowledge.ROOT", max_depth=2)
    second_result = engine.reason(graph, registry, "knowledge.ROOT", max_depth=2)

    assert first_result.status == "OK"
    assert first_result.traversed_node_ids == second_result.traversed_node_ids
    assert [chain.steps for chain in first_result.chains] == [chain.steps for chain in second_result.chains]
    assert "knowledge.CHILD" in first_result.traversed_node_ids
    assert any(chain.cross_domain for chain in first_result.chains)
    assert first_result.cross_domain_chain_count >= 1
    assert len(first_result.chains) == 3


def test_cross_domain_reasoning_engine_preserves_provenance_and_dependency_inference():
    registry = KnowledgeRegistry()
    source = KnowledgePattern(
        category="DOMAIN_A",
        frequency=1,
        pattern_id="knowledge.SOURCE",
        source_keys=("audit.execution.lineage.L-200",),
        provenance=(),
    )
    target = KnowledgePattern(
        category="DOMAIN_B",
        frequency=1,
        pattern_id="knowledge.TARGET",
        source_keys=("audit.execution.lineage.L-201",),
        provenance=("knowledge.SOURCE",),
    )

    registry.register(source)
    registry.register(target)

    graph = KnowledgeGraphEngine().build_graph(registry)
    original_nodes = len(graph.nodes)
    original_relationships = len(graph.relationships)
    original_dependencies = len(graph.dependencies)

    engine = CrossDomainReasoningEngine()
    result = engine.reason(graph, registry, "knowledge.TARGET", max_depth=1)

    assert result.status == "OK"
    assert result.cross_domain_chain_count == 1
    assert any(chain.cross_domain for chain in result.chains)
    assert any(
        step.transition_kind == "dependency"
        for chain in result.chains
        for step in chain.steps
    )
    assert any(
        "audit.execution.lineage.L-201" in step.provenance
        for chain in result.chains
        for step in chain.steps
    )
    assert len(graph.nodes) == original_nodes
    assert len(graph.relationships) == original_relationships
    assert len(graph.dependencies) == original_dependencies


def test_cross_domain_reasoning_engine_returns_no_records_for_unknown_start_id():
    registry = KnowledgeRegistry()
    graph = KnowledgeGraphEngine().build_graph(registry)
    engine = CrossDomainReasoningEngine()

    result = engine.reason(graph, registry, "knowledge.UNKNOWN", max_depth=2)

    assert result.status == "NO_RECORDS"
    assert result.chains == []
    assert result.issues == ["START_ID_NOT_FOUND"]

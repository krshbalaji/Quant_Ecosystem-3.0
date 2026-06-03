from quant_ecosystem.cognition.swarm import (
    KnowledgeDependency,
    KnowledgeGraph,
    KnowledgeGraphEngine,
    KnowledgeRelationship,
    KnowledgeRegistry,
    KnowledgePattern,
)


def test_knowledge_graph_engine_builds_graph_relationships_and_dependencies():

    registry = KnowledgeRegistry()

    base_pattern = KnowledgePattern(
        category="BASE",
        frequency=1,
        pattern_id="knowledge.BASE",
        pattern_type="event_type",
        source_keys=("audit.execution.lineage.L-1",),
        provenance=(),
    )
    derived_pattern = KnowledgePattern(
        category="DERIVED",
        frequency=2,
        pattern_id="knowledge.DERIVED",
        pattern_type="event_type",
        source_keys=("audit.execution.lineage.L-2",),
        provenance=("knowledge.BASE",),
    )
    composite_pattern = KnowledgePattern(
        category="COMPOSITE",
        frequency=3,
        pattern_id="knowledge.COMPOSITE",
        pattern_type="event_type",
        source_keys=("audit.execution.lineage.L-3", "audit.execution.lineage.L-4"),
        provenance=("knowledge.BASE", "knowledge.DERIVED"),
    )

    registry.register(base_pattern)
    registry.register(derived_pattern)
    registry.register(composite_pattern)

    engine = KnowledgeGraphEngine()
    graph = engine.build_graph(registry)

    assert set(graph.pattern_ids()) == {"knowledge.BASE", "knowledge.DERIVED", "knowledge.COMPOSITE"}
    assert any(rel.relationship_type == "derived_from" for rel in graph.relationships)
    assert len(graph.dependencies) == 4

    composite_relationships = [
        rel for rel in graph.relationships if rel.source_id == "knowledge.COMPOSITE"
    ]
    assert len(composite_relationships) == 2
    assert {rel.target_id for rel in composite_relationships} == {"knowledge.BASE", "knowledge.DERIVED"}


def test_knowledge_graph_engine_generates_lineage_graph_and_traversal():

    registry = KnowledgeRegistry()
    root = KnowledgePattern(
        category="ROOT",
        frequency=1,
        pattern_id="knowledge.ROOT",
        source_keys=("audit.execution.lineage.L-10",),
        provenance=(),
    )
    child = KnowledgePattern(
        category="CHILD",
        frequency=1,
        pattern_id="knowledge.CHILD",
        source_keys=("audit.execution.lineage.L-11",),
        provenance=("knowledge.ROOT",),
    )
    grandchild = KnowledgePattern(
        category="GRANDCHILD",
        frequency=1,
        pattern_id="knowledge.GRANDCHILD",
        source_keys=("audit.execution.lineage.L-12",),
        provenance=("knowledge.CHILD",),
    )

    registry.register(root)
    registry.register(child)
    registry.register(grandchild)

    engine = KnowledgeGraphEngine()
    graph = engine.build_graph(registry)
    lineage_graph = engine.generate_lineage_graph(graph, "knowledge.GRANDCHILD")

    assert lineage_graph.get_pattern("knowledge.GRANDCHILD") is not None
    assert lineage_graph.get_pattern("knowledge.CHILD") is not None
    assert lineage_graph.get_pattern("knowledge.ROOT") is not None
    assert any(dep.dependency_type == "audit_lineage" for dep in lineage_graph.dependencies)

    traversal = engine.traverse(graph, "knowledge.GRANDCHILD", max_depth=3)
    assert "knowledge.GRANDCHILD" in traversal
    assert "knowledge.CHILD" in traversal
    assert "knowledge.ROOT" in traversal


def test_knowledge_graph_engine_discovers_relationships_and_maps_dependencies():

    registry = KnowledgeRegistry()
    source = KnowledgePattern(
        category="SOURCE",
        frequency=1,
        pattern_id="knowledge.SOURCE",
        source_keys=("audit.execution.lineage.L-20",),
        provenance=(),
    )
    target = KnowledgePattern(
        category="TARGET",
        frequency=1,
        pattern_id="knowledge.TARGET",
        source_keys=("audit.execution.lineage.L-21",),
        provenance=("knowledge.SOURCE",),
    )

    registry.register(source)
    registry.register(target)

    engine = KnowledgeGraphEngine()
    graph = engine.build_graph(registry)

    relationships = engine.discover_relationships(graph, relationship_type="derived_from")
    dependencies = engine.map_dependencies(graph, dependency_type="audit_lineage")

    assert len(relationships) == 1
    assert relationships[0].source_id == "knowledge.TARGET"
    assert relationships[0].target_id == "knowledge.SOURCE"
    assert len(dependencies) == 2
    assert all(dep.dependency_type == "audit_lineage" for dep in dependencies)

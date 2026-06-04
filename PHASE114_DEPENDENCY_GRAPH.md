PHASE114A - QE3 ORGANISM DEPENDENCY GRAPH

Branch: `release/qe3-v1-institutional`
HEAD: `1cfde3ac818e785319c826bfffb36cc7be1d2cb9`
Baseline tests: 716 passed
Mode: read-only architecture census

## Census Method

Repository Python modules were scanned with an AST import census. Test modules were included as consumers because they reveal coverage and package export usage. Findings below use production consumer count unless explicitly noted.

Scope notes:

- Total Python modules found: 1,520
- Production/support modules: 1,183
- Test modules: 337
- Parse anomaly: `quant_ecosystem.core.engine_adapter` has an invalid non-printable `U+FEFF` marker and could not be parsed.

## Layer Counts

| Layer | Module Count | Risk | Recommendation |
|---|---:|---|---|
| Knowledge / learning / reasoning | 325 | HIGH | Assign explicit ownership boundaries; avoid adding new parallel engines without reuse review. |
| Execution | 150 | HIGH | Treat execution router and broker adapters as high-risk integration surfaces. |
| Registry | 78 | HIGH | Registry proliferation needs a catalog and canonical ownership map. |
| Foundation | 75 | HIGH | Signature churn must be guarded by compatibility tests. |
| Orchestration | 70 | HIGH | Multiple orchestrators/coordinators/routers should not be expanded without consolidation review. |
| Governance | 66 | MEDIUM | Current governance modules are fragmented but mostly low-consumer. |
| Persistence | 60 | HIGH | Persistence semantics are spread across stores, state managers, ledgers, archives, and DB clients. |
| Memory | 33 | MEDIUM | Memory surfaces are scattered across research, alpha, temporal, execution, and swarm layers. |
| Replay | 7 | MEDIUM | Replay is small but semantically duplicated between audit, knowledge, and recovery layers. |

## Core Producer Modules

These modules are consumed broadly and should be treated as foundation producers.

| Module | Dependency Count | Consumer Count | Risk | Recommendation |
|---|---:|---:|---|---|
| `quant_ecosystem.core.append_registry` | 0 | 30 | HIGH | Treat as a foundation API; freeze public behavior before registry consolidation. |
| `quant_ecosystem.strategies.base.base_strategy` | 0 | 16 | HIGH | Preserve base contract; require broad regression coverage for changes. |
| `quant_ecosystem.core.config_loader` | 0 | 14 | HIGH | Treat config loading as a system foundation; avoid parallel config loaders. |
| `quant_ecosystem.contracts.signal_intent` | 1 | 13 | HIGH | Maintain as canonical signal contract. |
| `quant_ecosystem.profiles.base_profile` | 0 | 13 | HIGH | Maintain stable profile interface. |
| `quant_ecosystem.cognition.swarm.knowledge_pattern` | 0 | 12 | HIGH | Treat as canonical knowledge artifact model. |
| `quant_ecosystem.contracts.profile_types` | 0 | 11 | MEDIUM | Keep as shared contract; document profile type ownership. |
| `quant_ecosystem.utils.decimal_utils` | 0 | 11 | MEDIUM | Keep low-level utility stable. |
| `quant_ecosystem.contracts.position` | 2 | 10 | MEDIUM | Preserve canonical position semantics. |
| `quant_ecosystem.canonical.broker_models` | 1 | 9 | MEDIUM | Treat as canonical broker/execution schema boundary. |
| `quant_ecosystem.core.multimap_store` | 0 | 8 | MEDIUM | Treat as foundation store primitive; do not add ad hoc stores around it without review. |

## Highest Import Fan-In Modules

These modules import many internal dependencies and are architectural aggregation points.

| Module | Dependency Count | Consumer Count | Risk | Recommendation |
|---|---:|---:|---|---|
| `quant_ecosystem.cognition.swarm` | 307 | 0 | HIGH | Package re-export hub is oversized; treat as import surface, not domain engine. |
| `quant_ecosystem.execution.execution_router` | 99 | 1 | HIGH | Split future changes by broker, routing, audit, and bridge boundaries before modifying. |
| `quant_ecosystem.core.system_factory` | 58 | 2 | HIGH | Maintain as composition root; avoid business logic growth. |
| `quant_ecosystem.core.master_orchestrator` | 17 | 1 | MEDIUM | Keep orchestration thin; do not add persistence or policy logic. |
| `quant_ecosystem.strategy_bank.strategy_universe` | 13 | 0 | MEDIUM | Confirm runtime entrypoint or demote to candidate for lifecycle review. |
| `integrations.tradingview_bridge` | 12 | 0 | MEDIUM | Verify external entrypoint; isolate from core runtime dependencies. |
| `quant_ecosystem.persistence` | 12 | 0 | MEDIUM | Package export hub should document persistence ownership. |
| `quant_ecosystem.execution_intelligence` | 11 | 0 | MEDIUM | Confirm role relative to execution and governance intelligence. |
| `quant_ecosystem.research` | 11 | 3 | MEDIUM | Keep package re-export behavior stable. |
| `strategy_loop` | 11 | 0 | MEDIUM | Verify legacy entrypoint before future cleanup. |
| `worker` | 11 | 0 | MEDIUM | Verify deployment entrypoint before future cleanup. |
| `quant_ecosystem.cognition.swarm.governance_intelligence_engine` | 10 | 1 | MEDIUM | Keep under PHASE113 read-only orchestration guardrails. |

## Special Focus Dependency Graph

| Module | Dependency Count | Consumer Count | Risk | Recommendation |
|---|---:|---:|---|---|
| `quant_ecosystem.execution.execution_router` | 99 | 1 | HIGH | Highest special-focus coupling; treat as execution composition root. |
| `quant_ecosystem.core.multimap_store` | 0 | 8 | MEDIUM | Foundation persistence primitive; document all sanctioned consumers. |
| `quant_ecosystem.cognition.swarm.governance_intelligence_engine` | 10 | 1 | MEDIUM | Thin orchestration is acceptable; avoid persistence, registry, routing, or execution hooks. |
| `quant_ecosystem.cognition.swarm.knowledge_graph_engine` | 5 | 2 | LOW | Reuse as graph builder; avoid parallel graph engines. |
| `quant_ecosystem.cognition.swarm.collective_learning_engine` | 5 | 2 | LOW | Keep as learning extraction layer; coordinate with consolidation. |
| `quant_ecosystem.cognition.swarm.sovereign_memory_replication_engine` | 4 | 1 | LOW | Document distributed-memory boundary before expanding. |
| `quant_ecosystem.cognition.swarm.cross_domain_reasoning` | 3 | 2 | LOW | Keep deterministic reasoning semantics stable. |
| `quant_ecosystem.cognition.swarm.governance_observability_engine` | 3 | 2 | LOW | Keep observe/register split explicit to preserve read-only composition paths. |
| `quant_ecosystem.cognition.swarm.distributed_memory_mesh` | 3 | 2 | LOW | Reuse for distributed-memory mesh behavior; avoid new mesh stores. |
| `quant_ecosystem.cognition.swarm.knowledge_consolidation_engine` | 3 | 1 | LOW | Treat persistence behavior as owned by consolidation, not governance intelligence. |
| `quant_ecosystem.cognition.swarm.knowledge_replay` | 2 | 2 | LOW | Reuse as canonical knowledge replay reader. |
| `quant_ecosystem.persistence.replay_recovery_engine` | 1 | 1 | LOW | Keep recovery distinct from forensic replay. |
| `quant_ecosystem.cognition.swarm.knowledge_registry` | 1 | 4 | LOW | Existing registry input; do not proliferate variants. |

## Import Graph Conclusions

- The organism has a broad set of low-dependency dataclass/model modules and a smaller set of very high fan-in/fan-out hubs.
- The largest dependency hub is `quant_ecosystem.cognition.swarm.__init__`, driven by re-export imports. This is not a runtime engine, but it is an import-surface risk.
- The largest functional hub is `quant_ecosystem.execution.execution_router`.
- Registry, orchestration, persistence, and knowledge layers are proliferated enough that future packs should require explicit reuse maps before new modules are added.
- Governance intelligence from Pack224A is medium coupling and compliant with the PHASE113 thin-orchestration decision.

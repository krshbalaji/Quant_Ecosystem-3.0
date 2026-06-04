PHASE114A - FOUNDATION USAGE REPORT

Mode: read-only architecture census

## Foundation Summary

Foundation modules are low-level contracts, base classes, registries, stores, configuration loaders, canonical models, and composition roots. The census found 75 foundation-classified production modules.

The most important foundation risk is not low usage; it is accidental churn in widely consumed modules.

## Foundation Producer Findings

| Module | Dependency Count | Consumer Count | Risk | Recommendation |
|---|---:|---:|---|---|
| `quant_ecosystem.core.append_registry` | 0 | 30 | HIGH | Treat as foundation registry API; require compatibility tests for changes. |
| `quant_ecosystem.strategies.base.base_strategy` | 0 | 16 | HIGH | Preserve strategy base interface. |
| `quant_ecosystem.core.config_loader` | 0 | 14 | HIGH | Maintain as canonical config loader or explicitly deprecate alternatives. |
| `quant_ecosystem.profiles.base_profile` | 0 | 13 | HIGH | Preserve profile base interface. |
| `quant_ecosystem.cognition.swarm.knowledge_pattern` | 0 | 12 | HIGH | Treat as knowledge artifact schema foundation. |
| `quant_ecosystem.canonical.broker_models` | 1 | 9 | MEDIUM | Treat as canonical execution/broker schema. |
| `quant_ecosystem.core.multimap_store` | 0 | 8 | MEDIUM | Treat as sanctioned multimap store primitive. |
| `config` | 0 | 7 | MEDIUM | Verify role relative to package configuration modules. |
| `quant_ecosystem.core.keyed_registry` | 0 | 6 | MEDIUM | Treat as generic keyed registry foundation. |
| `quant_ecosystem.execution.adapters.base_adapter` | 0 | 6 | MEDIUM | Preserve execution adapter contract. |
| `quant_ecosystem.portfolio.adapters.base_portfolio_adapter` | 0 | 6 | MEDIUM | Preserve portfolio adapter contract. |
| `quant_ecosystem.market.base_market_data` | 1 | 5 | MEDIUM | Preserve market data base contract. |
| `infra.logger` | 0 | 5 | MEDIUM | Shared logger utility; avoid silent behavior changes. |
| `quant_ecosystem.broker.base_broker` | 1 | 4 | MEDIUM | Preserve broker base contract. |
| `quant_ecosystem.canonical.market_models` | 1 | 4 | MEDIUM | Treat as canonical market schema. |
| `quant_ecosystem.core.registry_threading` | 1 | 4 | MEDIUM | Keep registry concurrency utility stable. |

## Persistence Foundation Findings

| Module | Dependency Count | Consumer Count | Risk | Recommendation |
|---|---:|---:|---|---|
| `quant_ecosystem.core.multimap_store` | 0 | 8 | MEDIUM | Centralize policy for shadow/learning/audit usage. |
| `firestore_client` | 0 | 6 | MEDIUM | Verify legacy/root persistence role relative to package persistence. |
| `quant_ecosystem.feature_lab.feature_store` | 0 | 5 | MEDIUM | Feature storage should remain research/feature scoped. |
| `quant_ecosystem.storage.organism_db` | 0 | 5 | MEDIUM | Treat as organism DB boundary; document callers. |
| `quant_ecosystem.state.state_manager` | 0 | 4 | MEDIUM | Keep runtime state ownership explicit. |
| `quant_ecosystem.execution.sovereignty.state_store` | 0 | 3 | MEDIUM | Keep execution sovereignty state separate from general persistence. |
| `quant_ecosystem.persistence.durable_snapshot_repository` | 0 | 3 | MEDIUM | Repository exists; document durable snapshot ownership. |
| `quant_ecosystem.persistence.in_memory_event_store` | 0 | 2 | MEDIUM | Keep event-store role distinct from `MultiMapStore`. |
| `quant_ecosystem.persistence.replay_recovery_engine` | 1 | 1 | LOW | Recovery replay only; do not reuse as forensic replay. |
| `quant_ecosystem.persistence.recovery_manager` | 1 | 0 | HIGH | No static production consumers; verify before expansion. |

## Knowledge Foundation Findings

| Module | Dependency Count | Consumer Count | Risk | Recommendation |
|---|---:|---:|---|---|
| `quant_ecosystem.cognition.swarm.knowledge_pattern` | 0 | 12 | HIGH | Canonical knowledge artifact. |
| `quant_ecosystem.cognition.swarm.knowledge_registry` | 1 | 4 | LOW | Existing knowledge registry; avoid variants. |
| `quant_ecosystem.cognition.swarm.knowledge_graph` | 3 | 3 | LOW | Canonical graph structure. |
| `quant_ecosystem.cognition.swarm.knowledge_graph_engine` | 5 | 2 | LOW | Canonical graph builder/traverser. |
| `quant_ecosystem.cognition.swarm.knowledge_replay` | 2 | 2 | LOW | Canonical knowledge replay reader. |
| `quant_ecosystem.cognition.swarm.cross_domain_reasoning` | 3 | 2 | LOW | Canonical deterministic reasoning layer. |
| `quant_ecosystem.cognition.swarm.governance_observability_engine` | 3 | 2 | LOW | Canonical governance observation summarizer. |
| `quant_ecosystem.cognition.swarm.governance_intelligence_engine` | 10 | 1 | MEDIUM | Thin read-only composition layer; do not promote to foundation store/registry. |

## Execution Foundation Findings

| Module | Dependency Count | Consumer Count | Risk | Recommendation |
|---|---:|---:|---|---|
| `quant_ecosystem.execution.execution_router` | 99 | 1 | HIGH | Highest-risk execution foundation; avoid broad edits. |
| `quant_ecosystem.canonical.broker_models` | 1 | 9 | MEDIUM | Canonical broker schema. |
| `quant_ecosystem.broker.broker_capabilities` | 0 | 6 | MEDIUM | Broker capability contract. |
| `quant_ecosystem.execution.adapters.base_adapter` | 0 | 6 | MEDIUM | Execution adapter base. |
| `quant_ecosystem.execution.execution_audit` | 1 | 5 | MEDIUM | Execution audit boundary. |
| `quant_ecosystem.contracts.order_intent` | 2 | 4 | LOW | Canonical order intent contract. |
| `quant_ecosystem.broker.base_broker` | 1 | 4 | LOW | Broker base contract. |
| `quant_ecosystem.oms.order_state_machine` | 1 | 4 | LOW | OMS state foundation. |
| `quant_ecosystem.oms.order_registry` | 1 | 3 | LOW | Order registry; keep execution-scoped. |

## Foundation Risks

| Finding | Module | Dependency Count | Consumer Count | Risk | Recommendation |
|---|---|---:|---:|---|---|
| Oversized package export | `quant_ecosystem.cognition.swarm` | 307 | 0 | HIGH | Keep as compatibility surface; consider future segmented exports. |
| Oversized execution root | `quant_ecosystem.execution.execution_router` | 99 | 1 | HIGH | Isolate responsibilities before future changes. |
| Composition-root fan-in | `quant_ecosystem.core.system_factory` | 58 | 2 | HIGH | Keep constructor wiring separate from domain behavior. |
| Generic registry centrality | `quant_ecosystem.core.append_registry` | 0 | 30 | HIGH | Document as canonical append registry. |
| Store primitive centrality | `quant_ecosystem.core.multimap_store` | 0 | 8 | MEDIUM | Prevent ad hoc persistence wrappers unless justified. |
| Parse anomaly | `quant_ecosystem.core.engine_adapter` | 0 | 0 | HIGH | Inspect BOM/non-printable marker before using module. |

## Foundation Usage Conclusions

- Foundations exist, but their ownership boundaries are uneven.
- `AppendRegistry`, `KeyedRegistry`, `MultiMapStore`, canonical broker/market/position models, and base adapters should be treated as protected APIs.
- The swarm package export surface is too broad to reason about as a single foundation.
- Future architecture work should document sanctioned foundation APIs before introducing new registries, stores, repositories, routers, or orchestration layers.

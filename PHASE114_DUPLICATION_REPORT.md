PHASE114A - DUPLICATION REPORT

Mode: read-only architecture census

## Duplication Summary

The repository shows capability duplication mainly by family proliferation: registries, routers/orchestrators, event buses, brokers, capital allocators, risk engines, memory stores, knowledge/governance model families, and persistence/replay surfaces.

This report does not recommend deletion. It recommends ownership mapping and parity audits before consolidation.

## Duplicate Capability Families

| Capability Family | Representative Modules | Dependency Count | Consumer Count | Risk | Recommendation |
|---|---|---:|---:|---|---|
| Registry | `quant_ecosystem.core.append_registry`, `quant_ecosystem.core.keyed_registry`, `quant_ecosystem.cognition.swarm.knowledge_registry`, `quant_ecosystem.cognition.swarm.federation_registry`, `quant_ecosystem.strategy_bank.strategy_registry` | 7 | 7 | HIGH | Assign canonical registry taxonomy: generic, typed-domain, and execution-only. |
| Decision | `quant_ecosystem.cognition.swarm.governance_decision_engine`, `quant_ecosystem.cognition.swarm.federation_decision_engine`, `quant_ecosystem.decision.decision_context`, `quant_ecosystem.cognition.swarm.architecture_decision_report` | 3 | 2 | HIGH | Separate decision records, decision engines, and decision context contracts. |
| Broker | `broker_adapter`, `infra.broker`, `quant_ecosystem.broker.base_broker`, `quant_ecosystem.broker.broker_router`, `quant_ecosystem.execution.execution_router` | 2 | 19 | HIGH | Make canonical broker boundary explicit; keep adapters below execution router. |
| Risk | `risk_engine`, `risk_manager`, `quant_ecosystem.risk.risk_engine`, `quant_ecosystem.cognition.swarm.federation_risk_engine`, `quant_ecosystem.strategy_execution.strategy_risk_controller` | 10 | 5 | HIGH | Create risk capability map before changing enforcement logic. |
| Portfolio | `portfolio_brain`, `portfolio_intelligence`, `quant_ecosystem.portfolio.portfolio_engine`, `quant_ecosystem.portfolio_ai.portfolio_ai_core`, `quant_ecosystem.portfolio.adapters.base_portfolio_adapter` | 10 | 12 | HIGH | Distinguish portfolio model, adapter, allocator, and intelligence roles. |
| Allocator | `capital_allocator`, `quant_ecosystem.capital_allocator.allocation_engine`, `quant_ecosystem.portfolio.capital_allocator`, `quant_ecosystem.strategy.capital_allocator`, `quant_ecosystem.core.capital.capital_allocator` | 5 | 3 | MEDIUM | Choose canonical allocation path per runtime layer. |
| Event Bus | `quant_ecosystem.core.event_bus`, `quant_ecosystem.events.event_bus`, `quant_ecosystem.event_engine.event_bus`, `quant_ecosystem.cognition.swarm.federation_event_bus`, `quant_ecosystem.oms.execution_event_bus` | 1 | 6 | MEDIUM | Document event bus scopes; avoid cross-wiring without adapter. |
| Market Data | `market_data_provider`, `quant_ecosystem.market.base_market_data`, `quant_ecosystem.market.market_data_engine`, `quant_ecosystem.market.market_data_router`, `quant_ecosystem.market_data.market_data_engine` | 2 | 9 | MEDIUM | Establish canonical market data model and router boundary. |
| Governance | `quant_ecosystem.governance`, `quant_ecosystem.cognition.swarm.governance_decision_engine`, `quant_ecosystem.cognition.swarm.governance_observability_engine`, `quant_ecosystem.core.capital.capital_governance_engine` | 8 | 0 | MEDIUM | Separate AI governance, execution governance, capital governance, and knowledge governance. |
| Intelligence | `quant_ecosystem.cognition.swarm.governance_intelligence_engine`, `quant_ecosystem.execution_intelligence`, `quant_ecosystem.core.capital.capital_intelligence_engine`, `quant_ecosystem.portfolio.capital_intelligence_engine` | 11 | 1 | MEDIUM | Add intelligence capability map before creating more intelligence engines. |
| Backtest | `quant_ecosystem.backtest.backtest_engine`, `quant_ecosystem.research.backtest.backtest_engine`, `quant_ecosystem.strategy_lab.backtest_engine` | 8 | 10 | MEDIUM | Document research vs strategy-lab vs production backtest boundaries. |
| Mutation | `quant_ecosystem.execution.governance.mutation_guard`, `quant_ecosystem.mutation_engine`, `quant_ecosystem.research.strategy_mutation_engine`, `quant_ecosystem.strategy_bank.mutation.mutation_engine` | 7 | 3 | MEDIUM | Keep execution mutation guards separate from strategy mutation engines. |
| Readiness | `quant_ecosystem.cognition.swarm.capability_readiness_engine`, `quant_ecosystem.cognition.swarm.federation_readiness_engine`, `quant_ecosystem.runtime.readiness_engine` | 2 | 1 | MEDIUM | Define runtime readiness vs federation readiness. |
| Trust | `quant_ecosystem.cognition.swarm.trust_registry`, `quant_ecosystem.cognition.swarm.federation_trust_registry`, `quant_ecosystem.cognition.swarm.federation_trust_engine`, `quant_ecosystem.cognition.swarm.trust_report` | 2 | 0 | MEDIUM | Keep trust metric/report/registry taxonomy explicit. |
| Replay | `quant_ecosystem.cognition.swarm.audit_replay`, `quant_ecosystem.cognition.swarm.knowledge_replay`, `quant_ecosystem.persistence.replay_recovery_engine`, `quant_ecosystem.persistence.recovery_manager` | 5 | 6 | MEDIUM | Distinguish forensic replay, knowledge replay, and recovery replay. |

## Registry Proliferation

| Module | Dependency Count | Consumer Count | Risk | Recommendation |
|---|---:|---:|---|---|
| `quant_ecosystem.core.append_registry` | 0 | 30 | LOW | Treat as generic append foundation. |
| `quant_ecosystem.core.keyed_registry` | 0 | 6 | LOW | Treat as generic keyed foundation. |
| `quant_ecosystem.cognition.swarm.knowledge_registry` | 1 | 4 | LOW | Treat as knowledge artifact registry. |
| `quant_ecosystem.cognition.swarm.federation_architecture_registry` | 2 | 4 | LOW | Keep as federation architecture registry unless merged by parity audit. |
| `quant_ecosystem.cognition.swarm.federation_capability_registry` | 2 | 4 | LOW | Keep as federation capability registry unless merged by parity audit. |
| `quant_ecosystem.cognition.swarm.federation_decision_registry` | 2 | 3 | LOW | Keep as federation decision registry unless merged by parity audit. |
| `quant_ecosystem.cognition.swarm.namespace_registry` | 1 | 3 | LOW | Keep as namespace registry; avoid duplicate namespace stores. |
| `quant_ecosystem.evolution.policy_registry` | 1 | 3 | LOW | Compare with governance policy modules. |
| `quant_ecosystem.oms.order_registry` | 1 | 3 | LOW | Keep execution/order-scoped. |
| `quant_ecosystem.profiles.profile_registry` | 8 | 2 | MEDIUM | High dependency count; review profile ownership. |
| `quant_ecosystem.cognition.swarm.execution_adapter_registry` | 2 | 2 | MEDIUM | Compare with root execution adapter registry. |
| `quant_ecosystem.cognition.swarm.orchestration_registry` | 1 | 2 | MEDIUM | Clarify role relative to workflow registries. |

## Orchestration Proliferation

| Module | Dependency Count | Consumer Count | Risk | Recommendation |
|---|---:|---:|---|---|
| `quant_ecosystem.execution.execution_router` | 99 | 1 | HIGH | Treat as execution composition root; avoid adding new responsibilities. |
| `quant_ecosystem.core.master_orchestrator` | 17 | 1 | MEDIUM | Keep as top-level orchestrator only. |
| `infra.execution_router` | 4 | 2 | MEDIUM | Clarify infra router vs package execution router. |
| `quant_ecosystem.cognition.swarm.federation_orchestrator` | 3 | 2 | MEDIUM | Keep federation-scoped; avoid runtime execution routing. |
| `quant_ecosystem.execution.mesh.mesh_coordinator` | 3 | 2 | MEDIUM | Keep mesh coordination scoped to execution mesh. |
| `quant_ecosystem.workflow.workflow_engine` | 2 | 2 | MEDIUM | Clarify workflow orchestration boundary. |
| `quant_ecosystem.api.orchestration_endpoint` | 1 | 2 | MEDIUM | Treat as API adapter only. |
| `quant_ecosystem.events.event_dispatch_router` | 1 | 2 | MEDIUM | Keep event routing separate from execution routing. |
| `quant_ecosystem.broker.broker_router` | 0 | 2 | MEDIUM | Clarify broker router beneath execution router. |
| `quant_ecosystem.research_orchestrator.research_pipeline_manager` | 2 | 2 | MEDIUM | Keep research orchestration separate from live runtime. |

## Replay Proliferation

| Module | Dependency Count | Consumer Count | Risk | Recommendation |
|---|---:|---:|---|---|
| `quant_ecosystem.cognition.swarm.audit_replay` | 2 | 2 | MEDIUM | Canonical forensic audit replay. |
| `quant_ecosystem.cognition.swarm.knowledge_replay` | 2 | 2 | MEDIUM | Canonical knowledge artifact replay. |
| `quant_ecosystem.persistence.replay_recovery_engine` | 1 | 1 | MEDIUM | Recovery replay; do not conflate with forensic replay. |
| `quant_ecosystem.persistence.persistence_recovery_manager` | 1 | 1 | MEDIUM | Recovery orchestration; keep write behavior explicit. |
| `quant_ecosystem.execution.governance.deadletter_recovery` | 1 | 1 | MEDIUM | Execution recovery; keep separate from audit replay. |
| `quant_ecosystem.execution.sovereignty.recovery_reconciler` | 0 | 1 | MEDIUM | Reconciliation layer; document mutation behavior. |
| `quant_ecosystem.persistence.recovery_manager` | 1 | 0 | HIGH | No production consumers; verify before expanding. |

## Duplication Conclusions

- Duplication is structural rather than simple copy-paste: similar concepts exist across root scripts, package modules, swarm federation modules, and execution/runtime modules.
- The highest-risk duplication families are registry, broker/execution routing, risk, portfolio, allocator, event bus, replay, and intelligence.
- Consolidation should be preceded by behavior parity audits; direct deletion or migration is not recommended from this census alone.

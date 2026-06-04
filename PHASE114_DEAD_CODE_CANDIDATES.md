PHASE114A - DEAD CODE CANDIDATES

Mode: static import census only

## Interpretation Guardrail

This report identifies modules with no production consumers by static import analysis. It does not prove dead code. Modules may still be used by CLIs, deployment commands, dynamic imports, scripts, dashboards, or external integrations.

No deletion is recommended in this phase.

## High-Risk Dead Code Candidates

| Module | Dependency Count | Consumer Count | Risk | Recommendation |
|---|---:|---:|---|---|
| `build_quant_ecosystem_3` | 0 | 0 | HIGH | Verify builder-script usage before deprecation. |
| `check_env` | 0 | 0 | HIGH | Verify local/operator CLI usage before deprecation. |
| `entry_timing` | 0 | 0 | HIGH | Confirm whether legacy signal timing path remains active. |
| `market_regime` | 0 | 0 | HIGH | Compare with `market_regime_intelligence` and package regime modules. |
| `pnl` | 0 | 0 | HIGH | Compare with accounting package before cleanup. |
| `pnl_tracker` | 0 | 0 | HIGH | Compare with accounting package before cleanup. |
| `portfolio_allocator_v2` | 0 | 0 | HIGH | Verify whether v2 is historical after v3/package allocators. |
| `precision_control` | 0 | 0 | HIGH | Verify execution usage before deprecation. |
| `broker` | 0 | 0 | HIGH | Package has no production consumers by static census; verify external import path. |
| `infra` | 0 | 0 | HIGH | Package init is isolated; submodules still have consumers. |
| `quant_ecosystem.Strategy_arena.strategy_registry` | 0 | 0 | HIGH | Registry proliferation candidate; compare with strategy-bank registry. |
| `quant_ecosystem.adapters` | 0 | 0 | HIGH | Weak package candidate; verify dynamic imports. |
| `quant_ecosystem.alpha_arena.alpha_tournament_engine` | 0 | 0 | HIGH | Verify research workflows before deprecation. |
| `quant_ecosystem.alpha_bank.alpha_competition` | 0 | 0 | HIGH | Verify alpha-bank runtime usage. |
| `quant_ecosystem.alpha_bank.alpha_scoring` | 0 | 0 | HIGH | Verify alpha-bank runtime usage. |
| `quant_ecosystem.autonomous_controller.autonomous_controller` | 0 | 0 | HIGH | Confirm autonomous controller entrypoint usage. |
| `quant_ecosystem.broker.broker_manager` | 0 | 0 | HIGH | Compare with broker router and execution router. |
| `quant_ecosystem.capital_allocator.layer` | 0 | 0 | HIGH | Verify package layer role. |
| `quant_ecosystem.cognition.swarm.governance_review_record` | 0 | 0 | HIGH | Unconsumed governance dataclass candidate. |
| `quant_ecosystem.core.boot_integration` | 0 | 0 | HIGH | Verify bootstrapping entrypoint usage. |
| `quant_ecosystem.core.capital.capital_allocator` | 0 | 0 | HIGH | Compare with other capital allocators. |
| `quant_ecosystem.core.capital.capital_intelligence_engine` | 0 | 0 | HIGH | Compare with portfolio intelligence modules. |
| `quant_ecosystem.core.dependency_manager` | 0 | 0 | HIGH | Confirm whether planned foundation module is active. |
| `quant_ecosystem.core.engine_adapter` | 0 | 0 | HIGH | Parse anomaly plus no consumers; inspect before future use. |
| `quant_ecosystem.core.execution_outcome_publisher` | 0 | 0 | HIGH | Verify execution event publication path. |
| `quant_ecosystem.core.maintenance_manager` | 0 | 0 | HIGH | Verify operator/maintenance entrypoint. |
| `quant_ecosystem.core.memory_event_adapter` | 0 | 0 | HIGH | Compare with memory lineage and replay adapters. |
| `quant_ecosystem.core.onboarding` | 0 | 0 | HIGH | Verify setup/onboarding script usage. |
| `quant_ecosystem.core.safety_controller` | 0 | 0 | HIGH | Compare with execution governance and safety governors. |
| `quant_ecosystem.core.state.system_state` | 0 | 0 | HIGH | Compare with state manager and snapshot engine. |
| `quant_ecosystem.core.system_health_monitor` | 0 | 0 | HIGH | Compare with telemetry/health modules. |
| `quant_ecosystem.core.system_integrity_check` | 0 | 0 | HIGH | Verify operator integrity-check path. |
| `quant_ecosystem.core.vcs.git_sync_manager` | 0 | 0 | HIGH | Verify deployment or maintenance usage. |
| `quant_ecosystem.evolution.capital_allocator` | 0 | 0 | HIGH | Compare with capital allocator variants. |
| `quant_ecosystem.evolution.distributed_alpha_grid` | 0 | 0 | HIGH | Verify alpha-grid evolution workflow. |
| `quant_ecosystem.evolution.genome_evaluator` | 0 | 0 | HIGH | Compare with alpha-genome evaluator. |
| `quant_ecosystem.evolution.meta_alpha_engine` | 0 | 0 | HIGH | Verify evolution workflow usage. |

## Weakly Connected But Not Necessarily Dead

| Module | Dependency Count | Consumer Count | Risk | Recommendation |
|---|---:|---:|---|---|
| `strategy_loop` | 11 | 0 | MEDIUM | High-dependency standalone entrypoint; verify deployment usage. |
| `worker` | 11 | 0 | MEDIUM | High-dependency standalone entrypoint; verify worker runtime usage. |
| `integrations.tradingview_bridge` | 12 | 0 | MEDIUM | Likely external webhook/bridge; verify outside Python import graph. |
| `quant_ecosystem.strategy_bank.strategy_universe` | 13 | 0 | MEDIUM | High-dependency module with no static consumers; verify runtime loader. |
| `quant_ecosystem.persistence` | 12 | 0 | MEDIUM | Package init may be export-only; verify external package import usage. |
| `quant_ecosystem.execution_intelligence` | 11 | 0 | MEDIUM | Package init may be export-only; verify consumers outside static imports. |
| `quant_ecosystem.alpha_genome` | 7 | 0 | LOW | Package export surface; verify external import usage. |
| `quant_ecosystem.autonomous_research` | 7 | 0 | LOW | Package export surface; verify planned research usage. |
| `quant_ecosystem.market_pulse` | 6 | 0 | LOW | Package export surface; verify planned market pulse usage. |
| `quant_ecosystem.research_memory` | 6 | 0 | HIGH | Memory package init with no production consumers; verify research-memory ownership. |

## Dead Code Conclusions

- Static dead-code candidates are numerous because this repository contains many package-level exports, scripts, and experimental subsystems.
- Do not remove anything based on this census alone.
- Next safe step would be a dynamic entrypoint census: CLI scripts, scheduled jobs, deployment configs, web routes, dashboards, and external integrations.

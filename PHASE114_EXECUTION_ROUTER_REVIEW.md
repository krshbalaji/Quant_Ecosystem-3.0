PHASE114B - EXECUTION ROUTER REVIEW

Target: `quant_ecosystem.execution.execution_router`
File inspected: `quant_ecosystem/execution/execution_router.py`
Mode: read-only architecture analysis

## Executive Finding

`quant_ecosystem.execution.execution_router` is a CRITICAL functional hotspot and the most urgent refactor candidate in the repository. Unlike `quant_ecosystem.cognition.swarm`, this module is not merely an export hub. It contains live execution behavior, broker adapters, broker routing, async queueing, snapshots, risk gates, canonical bridges, OMS integration, accounting integration, governance controls, adaptive components, and operator command methods in a single 4,956-line file.

## Hotspot Metrics

| Metric | Value | Classification |
|---|---:|---|
| Physical LOC | 4,956 | CRITICAL |
| Nonblank LOC | 4,277 | CRITICAL |
| AST import statements | 114 | CRITICAL |
| Classes defined locally | 19 | CRITICAL |
| Functions/methods defined locally | 159 | CRITICAL |
| Dependency fan-out | 99 | CRITICAL |
| Production consumer fan-in | 1 | LOW static fan-in, HIGH runtime criticality |
| Coupling score | 187 | CRITICAL |
| Cohesion score | 12 / 100 | LOW |
| God-object risk | CRITICAL | Multiple execution subsystems in one file |
| Refactor urgency | CRITICAL | Highest functional hotspot |

## Fan-In / Fan-Out Interpretation

Dependency fan-out: 99 internal dependencies. This is the second-largest fan-out in the repository and the largest functional fan-out.

Dependency fan-in: 1 production consumer by static import census. This low number does not reduce architectural risk because the module appears to be a runtime composition root and execution entrypoint.

## Responsibility Inventory

The module includes at least these responsibilities:

- paper broker implementation,
- Fyers/Zerodha/Binance broker adapter shims,
- multi-broker routing,
- broker health, resilience, failover, and selector logic,
- duplicate-order guard integration,
- retry/circuit-breaker behavior,
- liquidity/mutation/position truth/kill hierarchy governance,
- risk netting and correlation risk validation,
- async order queue,
- snapshot building,
- canonical order/modify/cancel payload bridging,
- portfolio and risk snapshot bridging,
- OMS order lifecycle bridge,
- OMS accounting bridge,
- live/paper execution orchestration integration,
- event ingestion,
- learning/adaptive broker selection hooks,
- regime/adaptive/metacognition/evolution/simulation/civilization hooks,
- operator command methods,
- synchronous and asynchronous execution shims,
- rebalance/liquidation assist logic.

This is a classic god-object/module pattern.

## Coupling Diagnosis

| Finding | Module | Dependency Count | Consumer Count | Risk | Recommendation |
|---|---|---:|---:|---|---|
| Functional fan-out hotspot | `quant_ecosystem.execution.execution_router` | 99 | 1 | CRITICAL | Do not add new responsibilities; split by execution boundary in future phases. |
| Broker adapter colocation | `quant_ecosystem.execution.execution_router` | 99 | 1 | HIGH | Move broker shims to adapter modules after behavior parity tests. |
| Routing and governance colocation | `quant_ecosystem.execution.execution_router` | 99 | 1 | HIGH | Separate broker routing from governance gates. |
| OMS/accounting bridge colocation | `quant_ecosystem.execution.execution_router` | 99 | 1 | HIGH | Move canonical/OMS/accounting bridges to dedicated bridge modules. |
| Adaptive/runtime intelligence imports | `quant_ecosystem.execution.execution_router` | 99 | 1 | HIGH | Gate adaptive imports behind smaller injected interfaces. |
| Operator command colocation | `quant_ecosystem.execution.execution_router` | 99 | 1 | MEDIUM | Move dashboard/operator command formatting out of execution core. |

## Cohesion Assessment

Cohesion score: 12 / 100.

Rationale:

- The file contains many execution-adjacent responsibilities, but they operate at different abstraction levels.
- Broker shims, routing, queues, snapshots, OMS bridges, accounting, risk, governance, learning, operator commands, and liquidation logic are not one cohesive unit.
- The file has high semantic coupling but low internal cohesion.

## God-Object Risk

Risk: CRITICAL.

Indicators:

- 4,956 physical lines.
- 19 local classes.
- 159 functions/methods.
- 99 internal dependencies.
- Direct imports from execution, broker, canonical, portfolio, OMS, accounting, events, instruments, strategy execution, governance, risk, capital, regime, telemetry, protection, learning, swarm, consensus, metacognition, evolution, simulation, reality, diplomacy, civilization, existential, constitution, and sentience layers.

## Refactor Urgency

Urgency: CRITICAL.

Reason:

- This module is a live execution root.
- It has high blast radius.
- It mixes execution behavior with adaptive/intelligence/governance layers.
- It is likely hard to review safely because unrelated changes can interact through shared state.

## Safe Future Refactor Slices

No refactor should happen during PHASE114B. Future work should proceed only with targeted tests and behavioral parity.

Recommended extraction order:

1. Broker adapter shims:
   - `_PaperBroker`
   - `_FyersBrokerAdapter`
   - `_ZerodhaBrokerAdapter`
   - `_BinanceBrokerAdapter`

2. Async queue and order item:
   - `OrderItem`
   - `AsyncOrderQueue`

3. Canonical bridges:
   - `CanonicalExecutionBridge`
   - `CanonicalPortfolioBridge`
   - `CanonicalRiskBridge`

4. OMS/accounting bridges:
   - `OMSBridge`
   - `OMSAccountingBridge`

5. Snapshot and reporting:
   - `SnapshotBuilder`
   - operator report methods

6. Risk/liquidation helpers:
   - exposure helpers,
   - rebalance assist,
   - liquidation assist.

7. Keep `ExecutionRouter` as a thin coordinator after extraction.

## Final Review Rating

Health: CRITICAL HOTSPOT.

`execution_router.py` should be treated as the first functional architecture refactor candidate. The initial goal should not be feature change. The initial goal should be isolating stable subcomponents while preserving all behavior.

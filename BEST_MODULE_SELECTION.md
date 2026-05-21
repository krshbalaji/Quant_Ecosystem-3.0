# Best Module Selection

Canonical decision: use `quant_ecosystem-3.0-git-FRESH` as the working base and recover selectively.

## Runtime Spine

| Layer | Canonical module | Reason |
|---|---|---|
| Entry | `main.py` -> `quant_ecosystem/core/system_factory.py` | Actual boot path creates `SystemRouter`, core layer, execution layer, strategy layer, optional intelligence/research layers. |
| Execution | `quant_ecosystem/execution/execution_router.py` | Full async router with paper mode, risk gates, queueing, and compatibility shims. |
| Broker routing | `quant_ecosystem/broker/broker_router.py` | Directly wired by `SystemFactory`; simple stable delegate. |
| Paper broker | `quant_ecosystem/broker/paper_broker.py` | Prefer package-level broker over minimal root fallback. |
| Risk | `quant_ecosystem/risk/risk_engine.py` | Wired in core boot; strongest risk authority. |
| Strategy registry | `quant_ecosystem/strategy_bank/engine/strategy_registry.py` | The registry imported by current strategy boot. |
| Signal pipeline | `quant_ecosystem/signals/*` and `quant_ecosystem/signal_engine/*` | Better architecture than root-only `signal_manager.py`; keep root manager as utility. |

## Research And Lifecycle

| Capability | Canonical module | Secondary recovery source |
|---|---|---|
| Autonomous loop | `quant_ecosystem/autonomous_research/autonomous_research_loop.py` | QE3 only if file-level diff shows newer logic. |
| Parameter optimization | `quant_ecosystem/adaptive_learning/parameter_optimizer.py` | Historical optimizer variants if tests expose gaps. |
| Backtest harness | FRESH `quant_ecosystem/synthetic_market/synthetic_backtester.py` | Smaller `quant_ecosystem/backtest/backtester.py` for CI-style reproducible tests. |
| Regime memory | `quant_ecosystem/intelligence/regime_memory.py` | Existing tests in `quant_ecosystem/tests/test_regime_memory.py`. |
| Strategy archive | `quant_ecosystem/strategy_lab/archived_strategies/` | Deleted `research_memory/performance_archive.py` as design input. |

## Monitoring And Ops

| Capability | Canonical module | Note |
|---|---|---|
| Telegram alerts | `telegram_notifier.py` and `quant_ecosystem/communication/telegram_notifier.py` | Keep config-gated; do not require network for startup validation. |
| Health/dashboard | `status.py`, `dashboard.py`, dashboard layer in `SystemFactory` | Add smoke checks after execution spine stabilizes. |
| Market data | `quant_ecosystem/market_data/*`, `market_data_provider.py`, `indicator_adapter.py` | Normalize into one provider contract before adding new adapters. |

## Non-Canonical Or Legacy

- Root `execution_engine_v2.py`: patched and syntax-valid, but standalone. It must not replace the `SystemFactory` -> `ExecutionRouter` path.
- Root `risk_engine.py`: smaller legacy variant. Keep only for compatibility until references are removed.
- Duplicate registries under `quant_ecosystem/core`, `quant_ecosystem/Strategy_arena`, and `quant_ecosystem/strategy_bank`: do not merge blindly. Establish one import path first.
- Live broker activation: out of scope for this recovery. Preserve paper-only posture.


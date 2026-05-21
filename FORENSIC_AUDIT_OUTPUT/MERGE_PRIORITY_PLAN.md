# MERGE PRIORITY PLAN (READ-ONLY)

Purpose: ordered priority plan for safe consolidation once you approve read-write work. This plan is evidence-based (from file-level inspection) but does not perform any merges — read-only only.

Priority 1 — Execution stability (High)
- Objective: fix correctness issues found in `execution_engine_v2.py` before merging execution pipeline.
- Evidence: undefined variables `entry_price`, `current_price` in `execution_engine_v2.py` (FRESH). Without this, automated exit logging and `ai_memory.record_trade` paths may fail.
- Files to review: `execution_engine_v2.py`, `precision_executor.py`, `quant_ecosystem/execution_router/*`.

Priority 2 — Broker adapters consolidation (High)
- Objective: unify adapter interfaces and expand unit tests for `coinswitch`, `fyers`, and other adapters.
- Files to review: `quant_ecosystem/broker/adapters/*` (FRESH, QE3, ARCHIVE), `broker_adapter.py`, `quant_ecosystem/broker/broker_router.py`.

Priority 3 — Backtest & paper harness convergence (Medium)
- Objective: adopt `quant_ecosystem/backtest/backtester.py` test harness and port robust synthetic/walk-forward logic from `synthetic_backtester.py` into a unified testing harness.
- Files to review: `quant_ecosystem/backtest/backtester.py`, `quant_ecosystem-3.0-git-FRESH/quant_ecosystem/synthetic_market/synthetic_backtester.py`, `test_backtest.py`.

Priority 4 — Risk + Strategy registry integration (Medium)
- Objective: ensure `risk_engine.allow_trade()` clear contract with strategy registry and execution router; add integration tests for sample signal → risk → execution flows.
- Files to review: `risk_engine.py`, `quant_ecosystem/strategy_bank/strategy_registry.py`, `signal_manager.py`.

Priority 5 — Market-data & indicators (Low-Medium)
- Objective: test `MarketDataProvider` and `IndicatorAdapter` for latency, edge-cases, and missing-data fallback; standardize return payloads.
- Files to review: `market_data_provider.py`, `indicator_adapter.py`, `quant_ecosystem/market_data/*`.

Priority 6 — Tests & CI (High ongoing)
- Objective: create focused unit and integration tests for broker adapters, execution router, risk-manager and the paper-to-live promotion gate.
- Evidence: tests exist in `quant_ecosystem/tests/` but integration tests are sparse; `quant_ecosystem` contains targeted backtest tests.

Operational notes:
- This is a recommended priority list for merging and hardening. It is intentionally conservative: fix concrete correctness issues before mass merges.
- All actions below require read-write confirmation. I will not perform merges until you explicitly authorize write operations.

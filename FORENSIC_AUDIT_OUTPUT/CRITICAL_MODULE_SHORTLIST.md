# CRITICAL MODULE SHORTLIST (READ-ONLY)

This shortlist enumerates concrete files (read-only) that contain candidate implementation to be reviewed/merged for each critical capability.

Broker
- quant_ecosystem-3.0-git-FRESH/quant_ecosystem/broker/broker_router.py — router abstraction
- quant_ecosystem-3.0-git-FRESH/quant_ecosystem/broker/adapters/ (all adapter files) — adapter implementations
- quant_ecosystem-3.0-git-FRESH/broker/paper_broker.py — simple paper broker
- quant_ecosystem-3.0-git/quant_ecosystem/broker/fyers_broker.py — alternate adapter

Execution
- quant_ecosystem-3.0-git-FRESH/execution_engine_v2.py — live engine (contains a bug to fix)
- quant_ecosystem-3.0-git-FRESH/precision_executor.py — precise execution wrapper
- quant_ecosystem-3.0-git-FRESH/quant_ecosystem/execution_router/ — router implementations
- QE3/quant_ecosystem/execution/ — compare for differing semantics

Paper trading / Backtesting
- quant_ecosystem/backtest/backtester.py — canonical backtest harness (unit tests reference)
- quant_ecosystem-3.0-git-FRESH/quant_ecosystem/synthetic_market/synthetic_backtester.py — synthetic/walk-forward backtester
- quant_ecosystem-3.0-git-FRESH/paper_trades.jsonl — trade log format used by risk engine

Strategy registry
- quant_ecosystem-3.0-git-FRESH/quant_ecosystem/strategy_bank/strategy_registry.py — registry class
- quant_ecosystem-3.0-git-FRESH/quant_ecosystem/strategy_bank/live_strategy_engine.py — live loader

Risk manager
- quant_ecosystem-3.0-git-FRESH/risk_engine.py — portfolio-aware risk engine
- quant_ecosystem-3.0-git-FRESH/quant_ecosystem/risk/ — supporting modules

Telegram alerts
- quant_ecosystem-3.0-git-FRESH/telegram_notifier.py — notifier wrapper
- QE3/test_telegram.py — test harness to validate tokens

Market data
- quant_ecosystem-3.0-git-FRESH/market_data_provider.py — provider with ATR computation
- quant_ecosystem-3.0-git-FRESH/indicator_adapter.py — higher-level indicator helpers

Research lab / Optimizer
- quant_ecosystem-3.0-git-FRESH/quant_ecosystem/autonomous_research/autonomous_research_loop.py — autonomous research loop
- quant_ecosystem-3.0-git-FRESH/quant_ecosystem/adaptive_learning/parameter_optimizer.py — optimizer implementation

Watchers / Scanners / Signal engine
- quant_ecosystem-3.0-git-FRESH/signal_manager.py — signal lifecycle
- quant_ecosystem-3.0-git-FRESH/quant_ecosystem/signals/ and `signal_engine/` — core signal pipeline

Notes for reviewers:
- Start with files in `quant_ecosystem-3.0-git-FRESH` as primary candidates, then compare with matching files in `quant_ecosystem-3.0-git` and `-ARCHIVE` for alternative implementations or historical fixes.
- `quant_ecosystem` (smaller repo) contains a focused `backtest/` harness that is useful to port/test against.

Strict read-only: these are file paths and candidate sources only; no file modifications performed.

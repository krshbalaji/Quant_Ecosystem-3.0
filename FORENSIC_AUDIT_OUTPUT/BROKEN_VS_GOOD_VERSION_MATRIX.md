# BROKEN vs GOOD VERSION MATRIX

This matrix compares duplicate implementations found across the workspace and identifies recommended canonical candidates (read-only evidence).

1) Risk Engine
- Candidates:
  - `risk_engine.py` (root): C:\Users\Home PLUS\Desktop\New folder (2)\quant_ecosystem-3.0-git-FRESH\risk_engine.py — simpler, smaller (line_count 112)
  - `quant_ecosystem/risk/risk_engine.py`: C:\Users\Home PLUS\Desktop\New folder (2)\quant_ecosystem-3.0-git-FRESH\quant_ecosystem\risk\risk_engine.py — full production-grade (line_count 479)
- Comparison/Recommendation:
  - Strongest / canonical: `quant_ecosystem/risk/risk_engine.py` — contains the comprehensive `RiskEngine` class, full API (`check_order`, `portfolio_exposure`, `symbol_exposure`, `allow_trade`) and is already wired by `SystemFactory`.
  - Broken/Regressed or legacy: root `risk_engine.py` appears to be a smaller or earlier variant; it lacks the full class-based API present in the canonical copy.
  - Missing features in root: full RiskEngine methods, dependency injection patterns, and integration points.

2) Execution Router / Execution Engine
- Candidates:
  - FRESH package: `quant_ecosystem/execution_router/` (layer.py + package) — lightweight layer and compatibility wrapper (line_count small)
  - QE3 implementation: `QE3/quant_ecosystem/execution/execution_router.py` — large, featureful, polyglot implementation (line_count ~2315)
  - Standalone engine: `execution_engine_v2.py` (root) — independent live engine script (contains NameError bug)
- Comparison/Recommendation:
  - Strongest / canonical: `QE3/quant_ecosystem/execution/execution_router.py` — largest, most complete implementation, rich API and many adapters. If import resolution uses it, it provides the fullest execution semantics.
  - FRESH execution_router package: smaller compatibility layer. Could be canonical if intentionally simplified, but lacks the deep implementation found in QE3.
  - Broken/regressed: `execution_engine_v2.py` is a standalone executor with a clear runtime bug (undefined `entry_price/current_price`). It should not be used as canonical live engine until fixed.
  - Missing features: FRESH layer may be missing advanced order queuing, async queue, multi-broker adapters found in QE3.

3) Broker / Adapter Implementations
- Candidates:
  - `broker/paper_broker.py` (FRESH root) — simple in-memory fallback
  - `quant_ecosystem/broker/paper_broker.py` — more featureful paper broker in package
  - `quant_ecosystem-3.0-git/quant_ecosystem/broker/fyers_broker.py` (quant_ecosystem-3.0-git) — full broker adapter
  - `quant_ecosystem/broker/adapters/fyers_adapter.py` (FRESH) — adapter-level implementation
- Comparison/Recommendation:
  - Strongest / canonical for production simulation: `quant_ecosystem-3.0-git\quant_ecosystem\broker\fyers_broker.py` — large and integrated with portfolio accounting.
  - For simple paper fallback: `broker/paper_broker.py` (FRESH) is acceptable but minimal; prefer `quant_ecosystem/broker/paper_broker.py` package copy for fuller features.
  - Adapter vs broker: adapters (`fyers_adapter.py`) provide protocol-specific code; broker wrapper (`fyers_broker.py`) integrates adapters into system-level semantics. Both are required; canonical set should include both adapter + broker wrapper from the more complete repo.

4) Backtest / Paper engines
- Candidates:
  - `quant_ecosystem/backtest/backtester.py` (quant_ecosystem repo) — focused harness used by unit tests
  - `quant_ecosystem-3.0-git-FRESH/quant_ecosystem/synthetic_market/synthetic_backtester.py` — large, walk-forward and robustness testing
- Comparison/Recommendation:
  - Strongest / canonical for research: `synthetic_backtester.py` in FRESH for advanced experimentation.
  - Strongest / canonical for reproducible unit backtests: `quant_ecosystem/backtest/backtester.py` (smaller, used by tests) — keep both: one for heavy research, one for unit/backtest CI.

5) Strategy Registry
- Candidates: multiple copies exist across `quant_ecosystem/core/strategy_registry.py`, `quant_ecosystem/strategy_bank/strategy_registry.py`, and `strategy_bank/engine/strategy_registry.py`.
- Comparison/Recommendation:
  - Strongest / canonical: `quant_ecosystem/strategy_bank/strategy_registry.py` in FRESH — used by SystemFactory to wire `LiveStrategyEngine`.
  - Duplicate copies should be consolidated to this single canonical implementation.

6) Telegram notifier
- Candidates: `telegram_notifier.py` in FRESH; `QE3/test_telegram.py` is a test harness.
- Recommendation: keep `telegram_notifier.py` as canonical, use `QE3/test_telegram.py` only as a validation harness.

Summary recommendations (read-only):
- Canonical base candidate: `quant_ecosystem-3.0-git-FRESH` (largest, most complete, contains wiring and system factory) — use this as canonical codebase for merges.
- Merge plan: adopt QE3's `execution_router.py` implementation if you require full execution semantics; otherwise, retain FRESH execution package but migrate missing features from QE3.
- Immediate safety fixes: do NOT run `execution_engine_v2.py` as-is; fix the NameError before execution. Prefer the ExecutionRouter-driven flow in `main.py`/SystemFactory.

If you want, I can produce exact per-line diffs between the candidate files (read-only) for any pair you specify (e.g., `quant_ecosystem/risk/risk_engine.py` vs root `risk_engine.py`).

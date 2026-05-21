# Cross-Repo Module Scorecard

Date: 2026-05-21
Canonical branch: `feature/pine-research-lab`
Canonical repo: `quant_ecosystem-3.0-git-FRESH`

Scoring: 5 = strongest canonical candidate, 4 = useful recovery source, 3 = partial/validation source, 2 = legacy/reference only, 1 = avoid unless explicitly needed.

| Capability | Best source | Score | Evidence | Selection posture |
|---|---:|---:|---|---|
| `execution_engine_v2.py` | `quant_ecosystem-3.0-git-FRESH/execution_engine_v2.py` | 3 | Standalone utility referenced by prior audit; confirmed NameError patch compiles. Not the canonical runtime path. | Keep as patched legacy utility; do not promote to canonical engine. |
| `execution_router.py` | `quant_ecosystem-3.0-git-FRESH/quant_ecosystem/execution/execution_router.py` | 5 | 2037-line async router with paper broker, risk gates, order queue, snapshots, and sync compatibility shims. Same-depth candidate also exists in `QE3`. | Canonical execution coordinator. Compare QE3 only for drift before importing anything. |
| `broker_router.py` | `quant_ecosystem-3.0-git-FRESH/quant_ecosystem/broker/broker_router.py` | 4 | Directly wired by `SystemFactory`; thin delegate around broker. | Keep canonical; harden with contract tests. |
| `broker_manager.py` | Cross-repo legacy broker folders | 2 | Deleted history shows pycache/legacy broker manager artifacts, but current runtime uses `BrokerRouter` plus broker wrappers. | Do not recover unless a live gap appears. |
| `paper_broker.py` | `quant_ecosystem-3.0-git-FRESH/quant_ecosystem/broker/paper_broker.py` | 4 | Package-level broker is stronger than root fallback; root `broker/paper_broker.py` is minimal. | Prefer package broker; keep root broker as fallback only. |
| `fyers_paper.py` / Fyers paper behavior | `quant_ecosystem-3.0-git-FRESH/quant_ecosystem/broker/fyers_broker.py` plus `quant_ecosystem-3.0-git` variant | 4 | `SystemFactory` initializes `FyersBroker(config=...)` as simulated broker in PAPER; older repo has alternate wrapper. | Keep FRESH first; inspect older wrapper before any adapter changes. |
| `risk_engine.py` | `quant_ecosystem-3.0-git-FRESH/quant_ecosystem/risk/risk_engine.py` | 5 | Wired by `SystemFactory`; prior audit records 479-line class with exposure and order checks. | Canonical risk authority. Root `risk_engine.py` is legacy. |
| `signal_manager.py` | `quant_ecosystem-3.0-git-FRESH/signal_manager.py` | 3 | Good lifecycle helper, but not clearly central runtime. Package signal engine/fusion modules are stronger architecture. | Keep as utility; route new work through package signal pipeline. |
| `strategy_registry.py` | `quant_ecosystem-3.0-git-FRESH/quant_ecosystem/strategy_bank/engine/strategy_registry.py` | 5 | Actually imported by `SystemFactory` strategy boot. Multiple other registries exist. | Canonical registry for runtime; consolidate aliases later. |
| `autonomous_research_loop.py` | `quant_ecosystem-3.0-git-FRESH/quant_ecosystem/autonomous_research/autonomous_research_loop.py` | 5 | 1321-line loop with discovery, mutation, evaluation, promotion, learning, and cycle status. | Canonical lifecycle loop. |
| `parameter_optimizer.py` | `quant_ecosystem-3.0-git-FRESH/quant_ecosystem/adaptive_learning/parameter_optimizer.py` | 4 | Focused optimizer with regime-row input contract. | Keep; add walk-forward/acid-test integration before promotion use. |
| `backtester.py` | `quant_ecosystem/backtest/backtester.py` and FRESH `synthetic_backtester.py` | 4 | Smaller repo has focused harness; FRESH has synthetic/walk-forward research backtester. | Keep both roles: CI harness from smaller repo, research harness in FRESH. |
| `telegram_notifier.py` | `quant_ecosystem-3.0-git-FRESH/telegram_notifier.py` plus package notifier | 3 | Present and simple; communication layer is config-gated. | Keep for alerts; add no-network dry-run test. |
| `market_data_provider.py` | `quant_ecosystem-3.0-git-FRESH/market_data_provider.py` | 4 | Dedicated provider with yfinance/pandas path; package market data engine is runtime layer. | Keep provider as adapter; normalize payloads into package market engine. |
| Drift monitor | `quant_ecosystem-3.0-git-FRESH` intelligence/monitoring modules | 3 | Capability appears present by naming and regime/intelligence modules, but needs contract validation. | Recover by contract, not blind merge. |
| Regime memory | `quant_ecosystem-3.0-git-FRESH/quant_ecosystem/intelligence/regime_memory.py` | 5 | Prior audit found implementation and tests. | Canonical monitoring memory. |
| Archive manager | Strategy lab/archive folders plus deleted `research_memory/performance_archive.py` | 3 | Strategy archives exist; deleted research memory archive modules are recoverable. | Rebuild as lifecycle archive service after registry schema is stable. |

Deleted-file recovery signals:
- High-value: `quant_ecosystem/research/backtest/backtest_engine_v2.py`, `quant_ecosystem/risk/risk_engine_v2.py`, `quant_ecosystem/market/market_data_engine1.py`, `quant_ecosystem/research_memory/*`.
- Low-value/noise: generated reports, pycache, venv binaries, old CSV outputs.


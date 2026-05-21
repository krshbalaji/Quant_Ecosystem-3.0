Purpose: Recommend the best source per capability based on completeness, recency, and ancillary artifacts (requirements, Dockerfile, README).

Capability -> Recommended Source (short justification)

- Broker: `quant_ecosystem-3.0-git-FRESH` — contains full `broker/`, adapters, router, and adapter scaffolding; most up-to-date.
- Execution: `quant_ecosystem-3.0-git-FRESH` — `execution_engine_v2.py`, `execution_router`, and precision executor present and integrated.
- Paper trading: `quant_ecosystem` — focused `backtest/` and `paper` related tests; use for validation harnesses.
- Backtesting: `quant_ecosystem` — explicit `backtest/` folder and unit tests (better for standalone backtests).
- Walk-forward: `quant_ecosystem-3.0-git-FRESH` — research orchestrator and research memory are most integrated here.
- Strategies / Registry: `quant_ecosystem-3.0-git-FRESH` — validated strategies, `strategy_lab`, and `strategy_bank` are well organized and documented.
- Risk manager: `quant_ecosystem-3.0-git-FRESH` — `risk_engine.py` and `risk_manager.py` alongside `risk/` modules.
- Portfolio manager: `quant_ecosystem-3.0-git-FRESH` — multiple allocator versions and `portfolio_brain` available.
- Telegram alerts: `quant_ecosystem-3.0-git-FRESH` — notifier, control and integration scripts centralized.
- Dashboard: `quant_ecosystem-3.0-git-FRESH` — `dashboard.py` and dashboard module present.
- Market data: `quant_ecosystem-3.0-git-FRESH` — `market_data_provider.py` plus `market_data` subsystems.
- Research lab / Optimizer / AI: `quant_ecosystem-3.0-git-FRESH` — integrated adaptive learning, `ai_engine.py`, and parameter optimizer presence favors FRESH.
- Monitoring / Health: `quant_ecosystem-3.0-git-FRESH` — `health_check.py`, status and monitoring utilities.
- Drift detection / Regime transition: `quant_ecosystem-3.0-git-FRESH` — `regime_transition`, `market_regime*` are current here.
- Execution logging / Trade manager / Watchers / Scanner / Signal engine: `quant_ecosystem-3.0-git-FRESH` — most consolidated, with QE3 and ARCHIVE as secondary sources.

Operational recommendation:
- Use `quant_ecosystem-3.0-git-FRESH` as the canonical base for feature consolidation and as the primary source for integration work.
- Use `quant_ecosystem` (the smaller repo) as the canonical source for backtesting and paper-trading harnesses and unit tests.
- Use `quant_ecosystem-3.0-git` and `-ARCHIVE` for recovering historical artifacts and deleted implementations when needed; treat them as secondary archives.

Notes:
- This audit is strictly read-only. No checkouts, commits, merges, or modifications were performed. Recommendations are based on directory presence, file counts, and repository artifacts (Dockerfile, README, requirements).
- If you want, I can next run a targeted file-level diff (read-only) for a short-list of modules (e.g., `broker/`, `execution/`, `strategy_lab/`) to extract concrete code-level differences and candidate files to merge.

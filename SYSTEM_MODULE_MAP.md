**SYSTEM MODULE MAP — quant_ecosystem-3.0-git-FRESH**

Overview: concise map of main modules and responsibilities discovered under `quant_ecosystem/` and project root.

- **Top-level orchestration & runners**:
  - `launcher.py`, `main.py`, `worker.py`, `run.bat`, `strategy_loop.py` — entrypoints and process supervisors.

- **Execution & Broker**:
  - `broker/` (root): `paper_broker.py` — lightweight paper executor.
  - `quant_ecosystem/broker/` and `quant_ecosystem/broker/adapters/`:
    - `coinswitch_broker.py`, `fyers_broker.py`, `paper_broker.py`
    - Adapters: `coinswitch_adapter.py`, `fyers_adapter.py` — CCXT-like adapter pattern.
  - `quant_ecosystem/execution/`: `execution_router.py`, `execution_planner.py`, `broker_router.py`, `unified_broker_router.py` — routing, policy, and order planning.

- **Market Data & Feature Store**:
  - `quant_ecosystem/market_data/market_data_engine.py` — ingestion engine.
  - `data/feature_store/` — feature persistence area.

- **Strategies & Strategy Infrastructure**:
  - `quant_ecosystem/strategies/` — strategy modules (trend, volatility, momentum, mean_reversion, microstructure).
  - `quant_ecosystem/strategy_lab/` — research lab, archived/validated strategies (many JSON strategy artifacts).
  - `quant_ecosystem/strategy_bank/`, `strategy_factory.py`, `strategy_bank_layer.py` — composition and registry.

- **Research / Evolution / Optimization**:
  - `quant_ecosystem/research/` — backtests, dataset builders, research daemons, factor engines.
  - `quant_ecosystem/alpha_genome/`, `alpha_arena/`, `alpha_bank/` — genome, mutation, scoring, tournaments.
  - `quant_ecosystem/research/grid/parallel_research_grid.py` and `strategy_mutation_engine.py` — distributed experimentation.

- **Decision / Intelligence / Regime**:
  - `quant_ecosystem/decision/` — `arbitration_engine.py`, `decision_context.py` (signal arbitration and decision contracts).
  - `quant_ecosystem/intelligence/` — regime_service, regime_memory, learning engines, global intelligence.

- **Risk & Capital**:
  - `quant_ecosystem/risk/` — `risk_engine.py`, `capital_allocator_v2.py`, `safety_layer.py`, `black_swan_guard.py`.

- **Telemetry, Monitoring & Control**:
  - `quant_ecosystem/control/`, `cockpit/` — control APIs and command routing.
  - `quant_ecosystem/communication/telegram_*` and root `telegram_*.py` — alerting & operator control.
  - `status.py`, `reporting/` — runtime telemetry and audits.

- **Storage & Persistence**:
  - `quant_ecosystem/storage/` — `trade_store.py`, other persistence helpers.
  - `paper_trades.jsonl`, `positions.json`, `seen_ids.json` in repo root.

- **Deployment / Cloud**:
  - `Dockerfile`, `cloudrun_app.py`, `requirements.txt`, `requirements-cloud.txt` — container + cloud run artifacts.

- **Utilities / Tools**:
  - `quant_master_builder.py`, `build_quant_ecosystem_3.py`, `quant_ecosystem_master_blueprint.py` — scaffolding and build helpers.

- **Noteworthy artifacts**:
  - `quant_ecosystem/strategy_lab/research_strategies/` and `archived_strategies/` — many JSON strategy artifacts (trend, momentum, volatility, mean_reversion, pairs trading, statistical arbitrage).
  - Legacy/fork artifacts found in git history and zip archives (see DEAD_CODE_RECOVERY.md).


---
Reference files used: directory listing of `quant_ecosystem/`, `quant_ecosystem/strategy_lab/`, `quant_ecosystem/broker/`, `quant_ecosystem/execution/`, and `quant_ecosystem/research/`.

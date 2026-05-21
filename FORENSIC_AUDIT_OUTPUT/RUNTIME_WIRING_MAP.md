# RUNTIME WIRING MAP — Truth Audit

Purpose: trace the actual launch path and which modules are wired and executed when running `main.py` (PAPER mode by default).

Entry points
- `main.py` — boots SystemFactory and starts the execution loop.
- `launcher.py` — runs `main()` via `asyncio`.

Boot sequence (observed in `quant_ecosystem/core/system_factory.py`)
1. Core layer (_boot_core_layer): initializes `SystemState`, `MarketDataEngine`, `RiskEngine`, `PortfolioEngine`, `OutcomeMemory`.
2. Execution layer (_boot_execution_layer) — PAPER mode default:
   - Try to create `FyersBroker` as paper/simulated broker.
   - Build `BrokerRouter` (thin delegate) around the broker.
   - Instantiate `ExecutionRouter` (import: `quant_ecosystem.execution.execution_router`).
   - Start execution loop (`start_execution_loop()` / `start()` / `run_forever()` depending on implementation).
3. Strategy layer (_boot_strategy_layer): constructs `StrategyRegistry` and `LiveStrategyEngine` and wires them into the ExecutionRouter.
4. Intelligence, safety, communication, research grid, autonomous research: optional and conditionally booted depending on config flags.

Concrete file-level wiring (what the factory imports and uses):
- SystemFactory: `quant_ecosystem/core/system_factory.py` — central wiring logic that decides what runs.
- ExecutionRouter: imported via `from quant_ecosystem.execution.execution_router import ExecutionRouter`.
- Broker implementations: prefers `quant_ecosystem.broker.fyers_broker.FyersBroker`; falls back to `broker/paper_broker.py` if unavailable.
- Broker router: `quant_ecosystem/broker/broker_router.py` is created and attached to router.
- Risk engine: `quant_ecosystem/risk/risk_engine.py` is instantiated in the core layer.
- Strategy registry and live engine: `quant_ecosystem/strategy_bank/strategy_registry.py` and `quant_ecosystem/strategy_bank/live_strategy_engine.py` are created and wired into the ExecutionRouter.

Runtime truth: WHAT ACTUALLY RUNS TODAY?
- Deterministic boot flow: `main.py` → `SystemFactory.build()` → core layer → execution layer → strategy layer → execution loop start. That is the canonical runtime path.
- Concrete modules that will execute on a default PAPER run (assuming no import failures):
  - `quant_ecosystem/risk/risk_engine.py` — YES (SystemFactory explicitly instantiates `RiskEngine`).
  - Broker: `quant_ecosystem.broker.fyers_broker.FyersBroker` — attempted; if instantiation fails, fallback `broker/paper_broker.py` is used — PAPER broker will run.
  - `quant_ecosystem.broker.broker_router.BrokerRouter` — YES (wrapped around the broker implementation).
  - `ExecutionRouter` — attempted via `quant_ecosystem.execution.execution_router`. Which concrete file is selected depends on import resolution: either the FRESH package `quant_ecosystem/execution_router` or the `QE3/quant_ecosystem/execution/execution_router.py` implementation. If import succeeds for an ExecutionRouter implementation, its `start_execution_loop()` is called by the factory.
  - `quant_ecosystem/strategy_bank/strategy_registry.py` and `quant_ecosystem/strategy_bank/live_strategy_engine.py` — YES (wired and propagated to ExecutionRouter).
  - `telegram_notifier.py` — only if `communication` boot step enables telegram (config-based); otherwise not started.
  - Market data providers (`market_data_engine`, `market_data_provider.py`, `indicator_adapter.py`) — only if `MarketDataEngine` initialization succeeds and is used by ExecutionRouter / Research layers.

Uncertainties and notes
- Import resolution determines which execution_router implementation is used. `SystemFactory` imports `quant_ecosystem.execution.execution_router` — if that package path exists in the active Python path it will load that implementation. The workspace contains multiple candidate implementations (FRESH `quant_ecosystem/execution_router/` and QE3 `quant_ecosystem/execution/execution_router.py`). Which one actually runs depends on `PYTHONPATH` and packaging when `main.py` runs.
- Many components are optional and gated by configuration flags (e.g., research grid, regime AI, event-driven engines). Their presence at runtime depends on the active `Config` values.
- The `execution_engine_v2.py` file (root) is a standalone live engine script. It is NOT directly referenced by `SystemFactory` — it is a separate engine script. It contains a runtime bug (NameError) and should not be executed as-is in production. See TOP_PRIORITY_CODE_FORENSICS.md for details.

Quick mapping of files to runtime role (summary):
- Entry: `main.py` → builds `SystemRouter` via `quant_ecosystem/core/system_factory.py`.
- Execution orchestration: `quant_ecosystem.execution.execution_router` (implementation file) → Execution loop → calls `broker_router.place_order()` / `broker.place_order()`.
- Broker implementations: `quant_ecosystem/broker/fyers_broker.py` (preferred) → `broker/paper_broker.py` fallback.
- Risk checks: `quant_ecosystem/risk/risk_engine.py` invoked by ExecutionRouter prior to submitting orders.
- Strategy discovery & live strategies: `quant_ecosystem/strategy_bank/*` wired into ExecutionRouter for live/paper runs.

If you want, I can now (read-only) produce a precise import-resolution table (file-level import hierarchy) showing exactly which implementation would be chosen when running `python main.py` with the current workspace PYTHONPATH — or run the startup in a safe dry-run to capture which `ExecutionRouter` is actually imported. Proceed on request.

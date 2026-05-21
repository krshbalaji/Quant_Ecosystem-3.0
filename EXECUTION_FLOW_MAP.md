**EXECUTION FLOW MAP — High-level flow**

Goal: describe how signals become orders in the existing repo.

1) Signal Generation & Research
  - Strategy definitions live in `quant_ecosystem/strategies/` and `quant_ecosystem/strategy_lab/`.
  - Research engines (`quant_ecosystem/research/`) produce validated strategy artifacts in JSON; strategy factory loads them.

2) Decision & Arbitration
  - `quant_ecosystem/decision/decision_context.py` carries signal metadata.
  - `quant_ecosystem/decision/arbitration_engine.py` selects / scores candidate signals, applies `arbitration` policies and outputs a `decision` object.

3) Execution Planning
  - Decision is routed to `quant_ecosystem/execution/execution_planner.py` and `execution_router.py` which translate decision into execution plans (order sizing, routing preferences).

4) Broker Routing
  - `quant_ecosystem/execution/broker_router.py` / `unified_broker_router.py` choose appropriate broker adapter.
  - Broker adapters under `quant_ecosystem/broker/adapters/` handle exchange-specific API calls.
  - Fallback: `broker/paper_broker.py` and `quant_ecosystem/broker/paper_broker.py` for paper execution and logging to `paper_trades.jsonl`.

5) Risk & Governance
  - `quant_ecosystem/risk/*` modules are consulted for position sizing, kill-switches, and pre-trade checks.

6) Persistence & Telemetry
  - Execution events are persisted to `quant_ecosystem/storage/trade_store.py` and `paper_trades.jsonl`.
  - `reporting/` and `telegram` modules push alerts and execution summaries.

Notes & actionables:
- To add live telemetry/telemetry-based arbitration, integrate normalized telemetry ingestion before step (2) and expose to `arbitration_engine` and `regime_service`.
- To make execution CCXT-compatible, introduce an adapter interface in `quant_ecosystem/broker/adapters/` and implement `BinanceAdapter`, `BybitAdapter`, plus `CoinSwitchFallbackAdapter`.

Reference files: `launcher.py`, `main.py`, `strategy_loop.py`, `quant_ecosystem/decision/arbitration_engine.py`, `quant_ecosystem/execution/*`, `quant_ecosystem/broker/*`.

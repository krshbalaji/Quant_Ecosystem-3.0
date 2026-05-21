# Architecture Final Map

Target state: paper-trading-ready, self-evolving quant ecosystem with selective recovered modules and one canonical runtime spine.

## Canonical Runtime Flow

```text
main.py
  -> SystemFactory.build()
     -> core layer
        -> SystemState
        -> MarketDataEngine
        -> RiskEngine
        -> PortfolioEngine
     -> execution layer
        -> FyersBroker in simulated/paper posture or no-op fallback
        -> BrokerRouter
        -> ExecutionRouter
     -> strategy layer
        -> StrategyRegistry
        -> LiveStrategyEngine
     -> optional layers
        -> intelligence/regime memory
        -> safety governor
        -> telegram/dashboard
        -> research grid
        -> autonomous research loop
```

## Research Layer

- Strategy discovery: `quant_ecosystem/strategy_discovery`, `quant_ecosystem/autonomous_research`.
- Pine donor ingestion/audit: recover as a strategy-lab adapter, not execution logic.
- Parameter optimization: `quant_ecosystem/adaptive_learning/parameter_optimizer.py`.
- Walk-forward and robustness: `quant_ecosystem/synthetic_market/synthetic_backtester.py`, plus smaller repo `backtest/backtester.py` as validation harness.
- Strategy scoring: strategy bank engines and autonomous research ranking.
- Archive obsolete strategies: strategy lab archive folders; recover deleted `research_memory/performance_archive.py` concepts only after schema lock.

## Execution Layer

- Broker abstraction: `quant_ecosystem/broker/broker_router.py`.
- Paper broker only: `quant_ecosystem/broker/paper_broker.py` and simulated `FyersBroker` path.
- Execution router: `quant_ecosystem/execution/execution_router.py`.
- Signal manager: package signal engine/fusion/ranker modules; root `signal_manager.py` remains compatibility utility.
- Order lifecycle: ExecutionRouter queue, fill accounting, broker router.
- Risk engine: `quant_ecosystem/risk/risk_engine.py`.
- Portfolio exposure control and sizing: risk engine, capital allocator, portfolio governor, position sizer.

## Data Layer

- Market data runtime: `quant_ecosystem/market_data/*` and market engine booted by `SystemFactory`.
- Provider adapters: `market_data_provider.py`, `indicator_adapter.py`.
- Multi-timeframe feeds: normalize provider payloads before adding new adapters.
- Crypto/equity adapters: use broker adapter interface; keep CoinSwitch/Fyers adapters isolated behind broker router.

## Monitoring Layer

- Telegram alerts: `telegram_notifier.py` and `quant_ecosystem/communication/*`.
- Dashboard: `dashboard.py` plus dashboard layer in `SystemFactory`.
- Health monitor: `status.py`, health modules.
- Drift detection: intelligence/monitoring modules need contract validation.
- Regime memory: `quant_ecosystem/intelligence/regime_memory.py`.
- Strategy degradation: implement as lifecycle service consuming trade store, regime memory, and strategy registry scores.

## Lifecycle Layer

- Autonomous research loop: `quant_ecosystem/autonomous_research/autonomous_research_loop.py`.
- Monitor -> enhance -> redeploy: autonomous loop plus strategy registry promotion gate.
- Archive failing strategies: lifecycle archive manager to be recovered or rebuilt after schema standardization.
- Promote only validated systems: require backtest, walk-forward, robustness, and paper-trade health gates.

## Integration Rules

- `SystemFactory` remains the dependency-injection authority.
- `ExecutionRouter` remains the only canonical order coordinator.
- `RiskEngine` must run before broker order submission.
- Live broker code may remain present but must not be enabled during recovery.
- Root-level scripts are compatibility utilities unless wired by `SystemFactory`.


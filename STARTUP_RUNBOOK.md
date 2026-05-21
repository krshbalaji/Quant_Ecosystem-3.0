# Startup Runbook

Goal: boot and validate the canonical ecosystem in paper/simulated mode only.

## Preflight

1. Confirm branch and dirty state.

```powershell
git status --short --branch
```

2. Confirm live trading is disabled in the shell.

```powershell
$env:TRADING_MODE='PAPER'
$env:LIVE_TRADING='false'
```

3. Run focused syntax validation for the currently patched file.

```powershell
python -m py_compile execution_engine_v2.py
```

4. Optional import-resolution check for the canonical router.

```powershell
python -c "from quant_ecosystem.execution.execution_router import ExecutionRouter; import inspect; print(inspect.getfile(ExecutionRouter))"
```

Expected path:

```text
...\quant_ecosystem-3.0-git-FRESH\quant_ecosystem\execution\execution_router.py
```

## Safe Startup

Use paper mode only:

```powershell
$env:TRADING_MODE='PAPER'
$env:LIVE_TRADING='false'
python main.py
```

Expected behavior:

- `SystemFactory.build()` logs mode `PAPER`.
- Core layer initializes state, market data, risk, and portfolio components.
- Execution layer initializes a simulated broker or no-op fallback.
- `ExecutionRouter` starts its loop.
- No live broker connection is required.

## Stop

Use `Ctrl+C`. The current `main.py` loop catches `KeyboardInterrupt` and logs shutdown.

## Troubleshooting

| Symptom | Likely cause | Action |
|---|---|---|
| `ExecutionRouter initialization failed` | Import or constructor mismatch | Inspect `quant_ecosystem/execution/execution_router.py` and `SystemFactory._boot_execution_layer`. |
| Fyers unavailable warning | Missing credentials or adapter dependency | Acceptable in paper recovery if no-op/paper fallback is used. |
| Telegram failures | Missing token/chat id or network disabled | Non-blocking for core paper startup. |
| Market mode says `HISTORICAL` despite `PAPER` | `REALITY_MODE=True` forces historical in `MarketModeController` | Treat as data-mode lock, not broker live mode; patch only after startup validation proves conflict. |
| Any live API attempt | Misconfigured mode or broker adapter | Stop immediately, set `TRADING_MODE=PAPER` and `LIVE_TRADING=false`, then inspect broker boot logs. |

## Promotion Gate

Do not promote a strategy to paper execution unless all pass:

- Backtest result exists.
- Walk-forward or synthetic robustness result exists.
- RiskEngine accepts the candidate exposure.
- Strategy registry metadata is complete.
- Paper execution dry run succeeds.
- Telegram/dashboard failure does not block execution safety.


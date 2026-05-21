# TOP PRIORITY CODE FORENSICS

This file contains strict read-only forensic entries for the prioritized shortlist (12 modules).

---

1) execution_engine_v2.py
- Exact path: C:\Users\Home PLUS\Desktop\New folder (2)\quant_ecosystem-3.0-git-FRESH\execution_engine_v2.py
- Repo: quant_ecosystem-3.0-git-FRESH
- File size (bytes): 2183
- Line count: 78
- Imports: requests, firestore_client, infra.broker, ai_memory (referenced)
- Classes: none
- Public functions: `fetch_price()`, `calculate_pnl()`, `process_positions()`
- TODO/FIXME markers: none present
- Syntax risk: BARE_EXCEPT_PRESENT (uses bare `except:` in `fetch_price`)
- Runtime risk: network I/O via `requests`, external firestore client, broker calls
- Undefined variables: exact broken use:
  - Line 68: `pnl = calculate_pnl(entry_price, current_price, side)` — `entry_price` and `current_price` are not defined in scope (variables are named `entry` and `current`). This causes a NameError at runtime.
  - Supporting line (context): Line 31 defines `entry = pos.get("entry_price")`.
- Dead code indicators: all three functions appear self-contained; no internal dead code flagged by heuristic.
- External dependency requirements: `requests`, `firestore_client`, `infra.broker`, `ai_memory`
- Referenced by which files: not found via basename search (invoked via runtime wiring through SystemFactory). See RUNTIME_WIRING_MAP.md for call path.
- Actually invoked at runtime? YES (SystemFactory boots ExecutionRouter which ultimately drives execution loop; `main.py` starts router and execution loop)
- Confidence score: 0.90

Notes: The critical runtime bug is the NameError on `entry_price/current_price`. Fix is to use `entry` and `current` or ensure the correct variable names are in scope; no patch applied (read-only audit).

---

2) precision_executor.py
- Exact path: C:\Users\Home PLUS\Desktop\New folder (2)\quant_ecosystem-3.0-git-FRESH\precision_executor.py
- Repo: quant_ecosystem-3.0-git-FRESH
- File size (bytes): 334
- Line count: 13
- Imports: none
- Classes: none
- Public functions: `execute_signal(symbol, side, qty, price, order_type="LIMIT")`
- TODO/FIXME markers: none
- Syntax risk: LOW
- Runtime risk: LOW
- Undefined variables: none detected
- Dead code indicators: function `execute_signal` not referenced elsewhere by basename heuristic (UNKNOWN runtime invocation)
- External dependency requirements: none declared
- Referenced by which files: none found
- Actually invoked at runtime? UNKNOWN
- Confidence score: 0.50

---

3) quant_ecosystem/execution_router/layer.py
- Exact path: C:\Users\Home PLUS\Desktop\New folder (2)\quant_ecosystem-3.0-git-FRESH\quant_ecosystem\execution_router\layer.py
- Repo: quant_ecosystem-3.0-git-FRESH
- File size (bytes): 478
- Line count: 14
- Imports: none
- Classes: `ExecutionRouterLayer`
- Public functions: `__init__`
- TODO/FIXME markers: none
- Syntax risk: LOW
- Runtime risk: LOW
- Undefined variables: none detected
- Dead code indicators: minimal; layer is a thin wrapper
- External dependency requirements: none declared
- Referenced by which files: none found via basename search
- Actually invoked at runtime? UNKNOWN (ExecutionRouter wiring is done via SystemFactory; exact implementation used determined at import resolution)
- Confidence score: 0.50

---

4) quant_ecosystem/broker/broker_router.py
- Exact path: C:\Users\Home PLUS\Desktop\New folder (2)\quant_ecosystem-3.0-git-FRESH\quant_ecosystem\broker\broker_router.py
- Repo: quant_ecosystem-3.0-git-FRESH
- File size (bytes): 656
- Line count: 30
- Imports: none
- Classes: `BrokerRouter`
- Public functions: `__init__`, `place_order`, `close_position`, `get_balance`, `get_orders`, `get_positions`, `get_account_snapshot`
- TODO/FIXME markers: none
- Syntax risk: LOW
- Runtime risk: LOW
- Undefined variables: none detected
- Dead code indicators: methods flagged by heuristic but expected to be used as thin delegate
- External dependency requirements: none declared (depends on injected broker implementation)
- Referenced by which files: SystemFactory and execution wiring (broker_router injected into router)
- Actually invoked at runtime? YES (wired into SystemFactory during boot if available)
- Confidence score: 0.90

---

5) broker/paper_broker.py (root)
- Exact path: C:\Users\Home PLUS\Desktop\New folder (2)\quant_ecosystem-3.0-git-FRESH\broker\paper_broker.py
- Repo: quant_ecosystem-3.0-git-FRESH
- File size (bytes): 301
- Line count: 14
- Imports: none
- Classes: `PaperBroker`
- Public functions: `place_order`, `close_position`, `get_positions`, `get_orders`, `get_balance`, `get_account_snapshot`
- TODO/FIXME markers: none
- Syntax risk: LOW
- Runtime risk: LOW
- Undefined variables: none detected
- Dead code indicators: simple in-memory implementation used as fallback
- External dependency requirements: none
- Referenced by which files: fallback paper broker references in SystemFactory if FyersBroker unavailable
- Actually invoked at runtime? YES (Paper broker is the default paper executor if live broker not present)
- Confidence score: 0.90

---

6) quant_ecosystem/backtest/backtester.py
- Exact path: C:\Users\Home PLUS\Desktop\New folder (2)\quant_ecosystem\backtest\backtester.py
- Repo: quant_ecosystem
- File size (bytes): 908
- Line count: 42
- Imports: pandas, numpy
- Classes: `Backtester`
- Public functions: `__init__`, `run`, `results`
- TODO/FIXME markers: none
- Syntax risk: LOW
- Runtime risk: LOW
- Undefined variables: none detected
- Dead code indicators: none flagged beyond routine methods
- External dependency requirements: `pandas`, `numpy`
- Referenced by which files: research/backtest integration (heuristic)
- Actually invoked at runtime? UNKNOWN (used by research/backtest harness rather than live execution)
- Confidence score: 0.50

---

7) quant_ecosystem/synthetic_market/synthetic_backtester.py
- Exact path: C:\Users\Home PLUS\Desktop\New folder (2)\quant_ecosystem-3.0-git-FRESH\quant_ecosystem\synthetic_market\synthetic_backtester.py
- Repo: quant_ecosystem-3.0-git-FRESH
- File size (bytes): 32269
- Line count: 759
- Imports: many internal modules (synthetic market engine, shock events, backtest engine helpers)
- Classes: `RegimeResult`, `RobustnessResult`, `SyntheticBacktester`, `_MinimalBacktestEngine`
- Public functions: large API (`run`, `walk_forward`, `evaluate_genome`, etc.)
- TODO/FIXME markers: none
- Syntax risk: LOW
- Runtime risk: LOW
- Undefined variables: none detected
- Dead code indicators: extensive API surface (most used by research loops)
- External dependency requirements: internal quant_ecosystem modules
- Referenced by which files: research/autonomous lab and synthetic market callers
- Actually invoked at runtime? UNKNOWN (wired into research grid when synthetic fallback is active)
- Confidence score: 0.50

---

8) quant_ecosystem/strategy_bank/strategy_registry.py
- Exact path: C:\Users\Home PLUS\Desktop\New folder (2)\quant_ecosystem-3.0-git-FRESH\quant_ecosystem\strategy_bank\strategy_registry.py
- Repo: quant_ecosystem-3.0-git-FRESH
- File size (bytes): 1099
- Line count: 44
- Imports: logging, typing
- Classes: `StrategyRegistry`
- Public functions: `__init__`, `load`, `register`, `unregister`, `get`, `list`, `clear`
- TODO/FIXME markers: none
- Syntax risk: LOW
- Runtime risk: LOW
- Undefined variables: none detected
- Dead code indicators: typical registration API; heuristic shows methods defined as expected
- External dependency requirements: logging
- Referenced by which files: SystemFactory boots `StrategyRegistry` and `LiveStrategyEngine`
- Actually invoked at runtime? YES
- Confidence score: 0.90

---

9) quant_ecosystem/risk/risk_engine.py
- Exact path: C:\Users\Home PLUS\Desktop\New folder (2)\quant_ecosystem-3.0-git-FRESH\quant_ecosystem\risk\risk_engine.py
- Repo: quant_ecosystem-3.0-git-FRESH
- File size (bytes): 19033
- Line count: 479
- Imports: __future__, logging, typing, quant_ecosystem.core.config_loader, time
- Classes: `_NullState`, `_NullConfig`, `RiskEngine`
- Public functions/methods: dozens — `check_order`, `portfolio_exposure`, `symbol_exposure`, `allow_trade`, `calculate_position_size`, etc.
- TODO/FIXME markers: none
- Syntax risk: LOW
- Runtime risk: LOW
- Undefined variables: none detected
- Dead code indicators: none — production-grade API
- External dependency requirements: quant_ecosystem core modules (Config, PortfolioEngine), standard library
- Referenced by which files: SystemFactory boots RiskEngine; ExecutionRouter references risk checks
- Actually invoked at runtime? YES
- Confidence score: 0.90

---

10) telegram_notifier.py
- Exact path: C:\Users\Home PLUS\Desktop\New folder (2)\quant_ecosystem-3.0-git-FRESH\telegram_notifier.py
- Repo: quant_ecosystem-3.0-git-FRESH
- File size (bytes): 433
- Line count: 18
- Imports: os, requests, dotenv
- Classes: none
- Public functions: `send_telegram(message)`
- TODO/FIXME markers: none
- Syntax risk: LOW
- Runtime risk: network I/O via `requests` and reliance on environment tokens
- Undefined variables: none detected
- Dead code indicators: function present; test harness `QE3/test_telegram.py` exists to validate tokens
- External dependency requirements: `requests`, `python-dotenv`
- Referenced by which files: not found via basename search — used by orchestration/dashboards when telegram configured
- Actually invoked at runtime? UNKNOWN (invoked if `telegram` engine is wired/configured)
- Confidence score: 0.50

---

11) market_data_provider.py
- Exact path: C:\Users\Home PLUS\Desktop\New folder (2)\quant_ecosystem-3.0-git-FRESH\market_data_provider.py
- Repo: quant_ecosystem-3.0-git-FRESH
- File size (bytes): 2238
- Line count: 77
- Imports: yfinance, pandas, time
- Classes: `MarketDataProvider`
- Public functions: `__init__`, `_safe_float`, `get_data`
- TODO/FIXME markers: none
- Syntax risk: LOW
- Runtime risk: network I/O via `yfinance`, depends on external network and pandas
- Undefined variables: none detected
- Dead code indicators: API surface used by indicator adapters and market engines
- External dependency requirements: `yfinance`, `pandas`
- Referenced by which files: market/engine modules and research datasets
- Actually invoked at runtime? UNKNOWN (used when market_data engine is booted)
- Confidence score: 0.50

---

12) signal_manager.py
- Exact path: C:\Users\Home PLUS\Desktop\New folder (2)\quant_ecosystem-3.0-git-FRESH\signal_manager.py
- Repo: quant_ecosystem-3.0-git-FRESH
- File size (bytes): 6148
- Line count: 254
- Imports: time
- Classes: none (module-level API)
- Public functions: `create_signal`, `get_signal`, `update_signal_status`, `update_qty`, `update_price`, `attach_message`, `mark_executed`, `mark_cancelled`, `mark_failed`, `cleanup_signals`, `has_active_signal`, `get_active_signal`, `print_signals`
- TODO/FIXME markers: none
- Syntax risk: LOW
- Runtime risk: in-memory state — not persisted; multi-process usage may lose signals
- Undefined variables: none detected
- Dead code indicators: full lifecycle implemented; used by UI/telegram flows and execution pipeline
- External dependency requirements: `time`
- Referenced by which files: execution pipeline, telegram flows, UI controllers (heuristic)
- Actually invoked at runtime? UNKNOWN (used by execution flows when signal pipeline wired)
- Confidence score: 0.50

---

End of forensic entries. For cross-repo diffs and duplicate comparisons see `BROKEN_VS_GOOD_VERSION_MATRIX.md`.

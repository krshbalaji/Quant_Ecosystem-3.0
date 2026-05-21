# Recovery Patch Plan

Mode: read-only by default. Patch only after a defect is confirmed by file evidence, import evidence, or a failing focused check.

## Completed Validation

1. `git status` inspected.
   - Branch: `feature/pine-research-lab`.
   - Modified tracked file: `execution_engine_v2.py`.
   - Existing recovery artifacts are untracked and preserved.
2. `git diff` inspected.
   - Existing patch adds Yahoo request timeout and replaces undefined `entry_price/current_price` with `entry/current` inside `record_trade`.
3. `execution_engine_v2.py` patch validated.
   - `python -m py_compile execution_engine_v2.py` succeeded.
   - Defect rationale is exact: original trailing-stop path could raise `NameError`.
4. Architecture/repair docs read.
   - Current docs consistently choose FRESH as canonical base and warn that `execution_engine_v2.py` is standalone.
5. Branches inspected.
   - Strong relevant historical branches include `feature/broker-guards`, `feature/execution-modes`, `feature/opportunity-dispatch`, `research_loop`, `regime_engine`, `regime_intelligence`, and `registry_sovereignty_lock`.
6. Deleted-file history inspected.
   - Recoverable signals: `risk_engine_v2.py`, `backtest_engine_v2.py`, `market_data_engine1.py`, `research_memory/*`, strategy archive JSON.
7. Duplicate-module map inspected.
   - FRESH has canonical package modules plus root-level legacy utilities; QE3 is primarily a deep execution-router comparison source.

## Patch Queue

### P0 - Keep Existing Confirmed Fix

- File: `execution_engine_v2.py`
- Status: already patched before this continuation.
- Rationale: confirmed runtime defect in trailing-stop exit logging path.
- Validation: syntax compile passed.
- No further code change required in this turn.

### P1 - Paper-Only Startup Guard

- Candidate files: `main.py`, `quant_ecosystem/core/market_mode.py`, `quant_ecosystem/core/system_factory.py`.
- Defect to confirm before patching:
  - `main.py` logs `TRADING_MODE` but does not pass the local `config` dict into `SystemFactory`.
  - `MarketModeController.set_mode(MarketMode.PAPER)` is immediately forced to `HISTORICAL` when `REALITY_MODE=True`, and `main.py` later calls `MarketMode.SYNTH`.
- Patch only if a startup smoke check proves paper-mode state is inconsistent or live-mode can be reached unintentionally.
- Intended patch if confirmed:
  - Pass an explicit config object into `SystemFactory`.
  - Force `TRADING_MODE=PAPER` unless a future live-trading feature flag is intentionally approved.
  - Remove or gate the post-build `SYNTH` mode flip.

### P2 - Execution Router Drift Check

- Candidate files:
  - `quant_ecosystem-3.0-git-FRESH/quant_ecosystem/execution/execution_router.py`
  - `QE3/quant_ecosystem/execution/execution_router.py`
- Observation: both inspected line counts are 2037 in this workspace snapshot.
- Patch only if a content diff shows QE3 contains missing guards or bugfixes.

### P3 - Broker/Paper Contract Tests

- Candidate files:
  - `quant_ecosystem/broker/broker_router.py`
  - `quant_ecosystem/broker/paper_broker.py`
  - `quant_ecosystem/broker/fyers_broker.py`
- Add tests before changing broker behavior.
- Required assertions:
  - Paper orders never call live broker APIs.
  - BrokerRouter returns stable order envelopes.
  - Positions/balance methods have predictable empty-state behavior.

### P4 - Strategy Registry Consolidation

- Candidate files:
  - `quant_ecosystem/strategy_bank/engine/strategy_registry.py`
  - `quant_ecosystem/strategy_bank/strategy_registry.py`
  - `quant_ecosystem/core/strategy_registry.py`
- Patch only after import-reference scan identifies all consumers.
- Goal: one runtime registry, compatibility shims elsewhere.

### P5 - Lifecycle Archive Recovery

- Candidate sources:
  - Deleted `quant_ecosystem/research_memory/performance_archive.py`
  - Existing `quant_ecosystem/strategy_lab/archived_strategies/`
- Patch only after schema is documented.
- Goal: archive failing strategies and promote only validated systems.

## No-Go Items

- Do not enable live trading.
- Do not delete or rewrite `RECOVERY_SNAPSHOT_20260521_120000/`.
- Do not mass-copy QE3 modules over FRESH.
- Do not replace `SystemFactory` with root-level legacy scripts.


**DEAD CODE RECOVERY — Candidates and Guidance**

Purpose: list deleted/archived modules (from git history and archived folders) that should be reviewed for recovery/merge.

Key findings from `git log` and repository archives:

- Many archived strategy artifacts in `quant_ecosystem/strategy_lab/archived_strategies/` and `research_strategies/` — these are high-value strategy definitions (trend, volatility, momentum, mean_reversion, pairs, stat arb). Recover by importing into `strategy_registry` and normalizing to a single metadata schema.

- Deleted files / snapshots (git history examples):
  - `quant_ecosystem-3.0 06.03.2026 15.48.zip`, `quant_ecosystem-3.0 07.03.2026 16.53.zip`, `quant_ecosystem-3.0 08.03.2026 08.08.zip` — full snapshots; unpack and inspect for missing modules.
  - `quant_ecosystem/docs/Quant_Ecosystem_Research_Architecture.zip` — architecture docs.
  - Several files with suffix `1` in git log (e.g., `market_data_engine1.py`, `global_intelligence_engine1.py`) indicate earlier iterations retained in history.
  - `New folder/*` artifacts (accidental duplicates): `live_strategy_engine.py`, `main.py`, `telegram_*` — check for newer versions.

Recovery recommendations:
- Step 1: Extract the ZIP snapshots listed in git history into a separate review folder (read-only copy) and diff against current codebase to find lost modules.
- Step 2: Pull archived strategy JSON files into `strategy_lab/` -> run a schema normalization script to convert to canonical strategy metadata.
- Step 3: For modules with duplicate/`1` suffixes (e.g., `market_data_engine1.py`), compare logic versions and keep the most complete implementation.
- Step 4: Re-enable recovered modules in feature branches and run unit tests. Prioritize research artifacts, broker adapters, and telemetry normalization.

Files flagged as potentially recoverable and high-priority:
- `quant_ecosystem/market/market_data_engine1.py` (git history)
- `quant_ecosystem/event_signal_engine/event_driven_signal_engine1.py`
- `quant_ecosystem/intelligence/global_intelligence_engine1.py`
- `quant_ecosystem/strategy_lab/*` archived JSON strategy artifacts (all)
- Zipped snapshots under repo root: `quant_ecosystem-3.0 *.zip`

Notes: Recovery must be done in feature branches; maintain read-only forensic copies of original archives before merging.

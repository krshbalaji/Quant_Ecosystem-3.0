**CAPABILITY GAP MATRIX — quant_ecosystem-3.0-git-FRESH**

Summary: quick assessment of present capabilities and gaps to prioritize modernization.

- Execution & Brokers
  - Present: Multiple broker adapters, router, paper broker.
  - Gap: No uniform CCXT adapter layer documented; adapters exist but vary in shape. Recommend an explicit CCXT-compatible adapter interface for Binance/Bybit and a coinswitch fallback.

- Market Data & Telemetry
  - Present: `market_data_engine.py`, feature store folder.
  - Gap: No clear live-market telemetry ingestion adapter implementing ATR/EMA slope/volatility percentile out-of-the-box. Add a telemetry normalization layer.

- Strategy Lifecycle
  - Present: Strategy factory, strategy lab with archived/validated strategies, live_strategy_engine.
  - Gap: Lack of standardized strategy metadata schema (some strategies are JSON artifacts, others are Python classes).

- Research / Auto-ML
  - Present: alpha_genome, mutation engines, parallel grid runner.
  - Gap: No packaged ML model serving or versioned model registry; limited integration with persistent model stores.

- Risk & Governance
  - Present: risk overlay, survival playbook, black swan guard.
  - Gap: Need clearer runtime kill-switches and automated execution throttles tied into telemetry (volatility/regime-aware controls).

- CI / Packaging
  - Present: `requirements.txt`, Dockerfile
  - Gap: Missing `pyproject.toml`, no GitHub Actions found; recommend adding packaging and CI to harden reproducibility.

- Observability & Alerts
  - Present: Telegram integrations and reporting outputs.
  - Gap: Centralized metrics/health dashboard (Prometheus/Grafana) not present; improve logging/metric export.

- Backups / Releases
  - Present: multiple zip snapshots and archived project zips in git history.
  - Gap: No canonical release artifact or versioning policy; consolidate into single master branch and release tags.

Priority recommendations:
- Implement CCXT-like adapter interface and add Binance & Bybit adapters first.
- Add live telemetry normalizer (multi-timeframe) and wire to `regime_service` and `arbitration_engine`.
- Add CI + packaging (`pyproject.toml`) and automated tests for telemetry and arbitration.


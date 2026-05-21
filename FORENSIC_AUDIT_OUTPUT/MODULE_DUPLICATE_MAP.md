Module | quant_ecosystem-3.0-git-FRESH | QE3 | quant_ecosystem | quant_ecosystem-3.0-git-ARCHIVE | Notes
---|---:|---:|---:|---:|---
broker/ | yes | yes | yes | yes | Core broker router + adapters exist in all repos; FRESH has the most recent adapter scaffolding.
execution/ execution_router/ precision_executor.py | yes | yes | partial | yes | Execution components duplicated; FRESH contains v2 engine and precision executor.
backtest/ | partial | partial | yes | partial | `quant_ecosystem` contains canonical `backtest/` with unit tests.
strategy_lab/ strategies/ strategy_bank/ | yes | yes | yes | yes | Strategy artifacts and archives present across repos (many JSON strategy files).
risk/ risk_engine.py | yes | yes | yes | yes | Multiple versions; FRESH has risk_manager and risk_engine files.
portfolio/ portfolio_allocator_v2.py | yes | yes | yes | yes | Portfolio allocators in FRESH (v2/v3) plus portfolio_ai in others.
telegram_control/ telegram_notifier.py | yes | yes | yes | yes | Telegram control present across repos, slightly different interfaces.
market_data/ market_data_provider.py | yes | yes | partial | yes | Market data engines duplicated; FRESH includes a dedicated provider.
research/ research_orchestrator/ | yes | yes | partial | yes | Research orchestration and memory exist in FRESH and QE3; archival copies in ARCHIVE.
adaptive_learning/ ai_engine.py | yes | partial | partial | yes | AI/ML modules spread across repos; FRESH integrates ai_engine and ai_memory.
signals/ signal_engine/ signal_factory/ | yes | yes | partial | yes | Signal pipeline duplicated; FRESH is most comprehensive.
scanners/ watchers/ indicator_adapter.py | yes | yes | yes | yes | Scanners and watchers duplicated; FRESH centralizes indicator adapters.
utils/ tools/ reporting/ | yes | yes | yes | yes | Common utilities duplicated; prefer FRESH for consolidated tools and docs.

# Quant Ecosystem 3.0 — Research Architecture

## Overview

This document describes the full self-evolving research architecture modelled after
Renaissance Medallion-style systematic research pipelines. Every component feeds
every other; the system improves itself continuously without human intervention.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                            QUANT ECOSYSTEM 3.0 — RESEARCH PIPELINE                         │
│                                                                                             │
│  ┌──────────────────────┐    ┌──────────────────────┐    ┌──────────────────────────────┐  │
│  │    DATA LAYER         │    │    FEATURE LAB        │    │    ALPHA GENOME PIPELINE     │  │
│  │                       │    │                       │    │                              │  │
│  │  MarketDataEngine     │───▶│  FeatureEngineering   │───▶│  AlphaGenePool               │  │
│  │  SymbolMapper         │    │  Engine               │    │  ↓                           │  │
│  │  CandleBuilder        │    │  FeatureStore         │    │  AlphaDNABuilder             │  │
│  │  MarketCache          │    │  IndicatorLibrary     │    │  ↓                           │  │
│  │                       │    │  (50+ indicators)     │    │  AlphaMutationEngine         │  │
│  │  ResearchDataset      │    │                       │    │  AlphaCrossoverEngine        │  │
│  │  Builder              │    │  Features:            │    │  ↓                           │  │
│  │  FactorDataset        │    │  • Trend (8 features) │    │  GenomeEvaluator             │  │
│  │  Builder              │    │  • Momentum (9)       │    │  (backtest + shadow)         │  │
│  └──────────────────────┘    │  • Volatility (9)     │    └──────────────────────────────┘  │
│                               │  • Volume (6)         │                ↓                    │
│  ┌──────────────────────┐    │  • Statistical (5)    │    ┌──────────────────────────────┐  │
│  │  SIGNAL FACTORY       │◀───│                       │    │  DISTRIBUTED RESEARCH        │  │
│  │                       │    └──────────────────────┘    │  (Ray parallel)              │  │
│  │  SignalGenerator      │                                 │                              │  │
│  │  Engine               │    ┌──────────────────────┐    │  ResearchPipelineManager     │  │
│  │  (8 rule types)       │◀───│  META ALPHA ENGINE    │    │  • 100s genomes/cycle        │  │
│  │                       │    │                       │    │  • Ray remote eval           │  │
│  │  SignalFilter         │    │  RegimeDetection      │───▶│  • Filter + promote          │  │
│  │  Engine               │    │  Engine               │    │                              │  │
│  │  • Regime filter      │    │  • Trend layer        │    │  ResearchScheduler           │  │
│  │  • Strength filter    │    │  • Vol layer          │    │  • 300s cycle interval       │  │
│  │  • Correlation filter │    │  • Stat layer         │    │  • 1h evolution run          │  │
│  │  • Cooldown filter    │    │  • Ensemble vote      │    │                              │  │
│  │  • Exposure filter    │    │                       │    │  ExperimentTracker           │  │
│  │                       │    │  AlphaCombination     │    │  • Full lineage              │  │
│  │  SignalQuality        │    │  Engine               │    │  • IC/fitness history        │  │
│  │  Engine               │    │  • IC-weighted        │    └──────────────────────────────┘  │
│  │  • IC (Spearman)      │    │  • Rank-weighted      │                ↓                    │
│  │  • IR                 │    │  • Majority vote      │    ┌──────────────────────────────┐  │
│  │  • Hit rate           │    │  • Regime adaptive    │    │  STRATEGY LAB                │  │
│  │  • Decay halflife     │    │                       │    │                              │  │
│  └──────────────────────┘    │  EnsembleSignal        │    │  StrategyLab Controller      │  │
│           ↓                   │  Engine               │    │  ShadowTrading               │  │
│  ┌──────────────────────┐    │  • Regime-conditional │    │  PromotionEvaluator          │  │
│  │  EXECUTION            │    │    model weights      │    │  StrategyBank                │  │
│  │                       │◀───│  • IC-adaptive        │    └──────────────────────────────┘  │
│  │  ExecutionRouter      │    └──────────────────────┘                ↓                    │
│  │  RiskEngine           │                                 ┌──────────────────────────────┐  │
│  │  PortfolioEngine      │    ┌──────────────────────┐    │  ADAPTIVE FEEDBACK            │  │
│  │  CapitalAllocator     │    │  ORCHESTRATION        │    │                              │  │
│  │                       │    │                       │    │  AdaptiveLearning            │  │
│  │  MasterOrchestrator   │◀───│  30-cycle trading     │    │  Engine                      │  │
│  │                       │    │  loop                 │    │  StrategySurvival            │  │
│  │  FyersBroker          │    │  Regime refresh       │    │  StrategyDiversity           │  │
│  │  (live/paper)         │    │  Feature refresh      │    │  MetaBrain                   │  │
│  └──────────────────────┘    │  Signal generation    │    └──────────────────────────────┘  │
│                               └──────────────────────┘                                      │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Dependency Flow

```
MarketDataEngine
    └─▶ FeatureEngineeringEngine
            └─▶ FeatureStore (persist)
            └─▶ SignalGeneratorEngine
                    └─▶ SignalFilterEngine
                            └─▶ AlphaCombinationEngine
                                    └─▶ EnsembleSignalEngine
                                            └─▶ ExecutionRouter

AlphaGenePool
    └─▶ AlphaDNABuilder
            └─▶ AlphaMutationEngine
            └─▶ AlphaCrossoverEngine
                    └─▶ ResearchPipelineManager (Ray)
                            └─▶ GenomeEvaluator
                                    └─▶ StrategyLab → promotion
                                    └─▶ ExperimentTracker (record)

RegimeDetectionEngine
    └─▶ SignalFilterEngine.update_regime()
    └─▶ AlphaCombinationEngine.update_regime()
    └─▶ EnsembleSignalEngine.update_regime()
    └─▶ StrategySelector (existing)
    └─▶ CapitalAllocatorEngine (existing)

SignalQualityEngine
    └─▶ receives: RawSignal (from SignalGeneratorEngine)
    └─▶ receives: resolve() calls (from trade results via AdaptiveLearning)
    └─▶ outputs:  IC, IR, hit_rate per strategy_id
    └─▶ feeds:    AlphaCombinationEngine weights
    └─▶ feeds:    EnsembleSignalEngine per-model weights

ResearchScheduler
    └─▶ research_pipeline_cycle (every 5 min): 50 genomes evaluated
    └─▶ evolution_full_run (every 1 hour): 500 genomes, 10 generations
    └─▶ feature_refresh: every trading cycle
```

---

## Module Placement

```
quant_ecosystem/
│
├── feature_lab/                     ← NEW
│   ├── __init__.py
│   ├── feature_engineering_engine.py
│   ├── feature_store.py
│   └── indicator_library.py
│
├── alpha_genome/                    ← EXTENDED (4 new files)
│   ├── alpha_gene_pool.py           ← NEW
│   ├── alpha_dna_builder.py         ← NEW
│   ├── alpha_mutation_engine.py     ← NEW
│   ├── alpha_crossover_engine.py    ← NEW
│   ├── genome_generator.py          ← existing
│   ├── genome_mutator.py            ← existing
│   ├── genome_crossbreeder.py       ← existing
│   ├── genome_evaluator.py          ← existing
│   └── genome_library.py            ← existing
│
├── signal_factory/                  ← NEW
│   ├── __init__.py
│   ├── signal_generator_engine.py
│   ├── signal_filter_engine.py
│   └── signal_quality_engine.py
│
├── meta_alpha_engine/               ← NEW
│   ├── __init__.py
│   ├── regime_detection_engine.py
│   ├── alpha_combination_engine.py
│   └── ensemble_signal_engine.py
│
├── research_orchestrator/           ← NEW
│   ├── __init__.py
│   ├── research_pipeline_manager.py
│   ├── experiment_tracker.py
│   └── research_scheduler.py
│
├── data_layer/                      ← NEW
│   ├── __init__.py
│   ├── research_dataset_builder.py
│   └── factor_dataset_builder.py
│
├── core/
│   ├── system_factory.py            ← PATCH (see integration_patches.py)
│   └── master_orchestrator.py       ← PATCH (see integration_patches.py)
│
└── evolution/
    ├── alpha_evolution_engine.py    ← PATCH (see integration_patches.py)
    └── distributed_research_engine.py ← REPLACE (see integration_patches.py)
```

---

## Integration Steps

### Step 1 — system_factory.py

Open `quant_ecosystem/core/system_factory.py`. At the top, add all imports from
`integration_patches.SYSTEM_FACTORY_IMPORTS`. Inside `SystemFactory.build()`, after
the `router = ExecutionRouter(...)` block and before `return router`, paste
`integration_patches.SYSTEM_FACTORY_BUILD_ADDITIONS`.

### Step 2 — distributed_research_engine.py

Replace `quant_ecosystem/evolution/distributed_research_engine.py` with the
content in `integration_patches.DISTRIBUTED_RESEARCH_ENGINE`. This gives you a
production Ray-powered evaluation loop instead of the stub.

### Step 3 — alpha_evolution_engine.py

In `quant_ecosystem/evolution/alpha_evolution_engine.py`:
1. Replace the `evolve()` method with `integration_patches.ALPHA_EVOLUTION_ENGINE_EVOLVE`
2. Add `attach_ecosystem_engines()` method to the class

### Step 4 — master_orchestrator.py

In `MasterOrchestrator.__init__`:
- Append `integration_patches.ORCHESTRATOR_INIT_ADDITIONS`

In `_run_institutional_cycle`:
- Append `integration_patches.ORCHESTRATOR_INSTITUTIONAL_CYCLE_ADDITIONS`

After `router = factory.build()` in main or launcher:
```python
orchestrator._attach_research_ecosystem(router.system)
```

### Step 5 — requirements.txt (rename from requests.txt)

```
# Core
numpy>=1.26
pandas>=2.1
scipy>=1.12

# Broker
fyers-apiv3
python-dotenv
requests
aiohttp>=3.9

# Research
ray[default]>=2.9
scikit-learn>=1.4

# Async / server
uvicorn[standard]
fastapi

# Monitoring
loguru
```

---

## Scaling to 1000s of Strategies Per Day

### Current bottleneck: sequential genome evaluation

The existing `BacktestEngine._generate_prices()` uses pure Python with random simulation.
For 1000 strategies/day you need:

**1. Vectorized backtest (replace BacktestEngine)**
```python
# Instead of Python loop, use numpy vectorized operations:
# signals shape: (N_strategies, T_bars) 
# returns shape: (T_bars,)
# pnl matrix:    (N_strategies, T_bars) = signals * returns
pnl_matrix = signals * returns_broadcast   # vectorized, 100x faster
```

**2. Ray parallelism (already integrated)**
```python
# ResearchPipelineManager._ray_evaluate() submits all genomes in one shot:
futures = [evaluate_genome_distributed.remote(g, periods) for g in genomes]
results = ray.get(futures)   # waits for all 1000 in parallel
```

**3. Batched feature computation**
```python
# DistributedResearchEngine.compute_features_batch() runs all symbols in parallel:
futures = [compute_features_distributed.remote(sym, ohlcv) for sym, ohlcv in symbol_ohlcv_map.items()]
```

**4. Tiered scheduling**
```
Every  5 min:  50 genome quick eval      (signal rule proxy backtest, ~0.1s each)
Every  1 hour: 500 genome full eval       (full vectorized backtest, 1s each = 8min on 4 cores)
Every  6 hours: 2000 genome evolution run (Ray cluster, 10 min on 16 cores)
```

**5. Gene pool pruning**
```python
gene_pool.prune(min_fitness=-0.5, keep_top=200)   # run nightly
```

**6. Feature store caching**
Feature computation is expensive. The FeatureStore 2-layer cache means features
computed at bar N are reused for all 1000 strategy evaluations at that bar — not
recomputed per genome.

**7. Deployment topology for max throughput**

```
┌─────────────────────┐
│  Head Node          │  ← MasterOrchestrator + trading loop
│  Ray head           │
└─────────┬───────────┘
          │ Ray cluster
    ┌─────┴──────┐
    ▼            ▼
┌────────┐  ┌────────┐   ← 4 worker nodes × 4 cores = 16 parallel evaluations
│Worker 1│  │Worker 2│     Each evaluates 50 genomes → 800 genomes / 10 min
└────────┘  └────────┘
```

---

## Performance Improvements Over Current System

| Area | Current | With New Modules | Speedup |
|---|---|---|------|
| Feature computation | Per-cycle, Python loops | Vectorized numpy, cached | 20x |
| Genome evaluation | Sequential, proxy only | Ray parallel + vectorized | 50x |
| Signal generation | Strategy loop → execution | Rule-based, batch | 5x |
| Regime detection | Single intelligence engine | Multi-layer ensemble | Better accuracy |
| Strategy quality | Sharpe only | IC + IR + decay | More rigorous |
| Gene pool warm-start | Cold start every session | AlphaGenePool persisted | Continuous |
| Experiment tracking | None | ExperimentTracker full lineage | Audit + replay |
| Factor research | None | FactorDatasetBuilder + IC | Cross-sectional alpha |

---

## Regime → Strategy Routing Table

| Regime | Best Strategies | Avoid |
|---|---|---|
| TRENDING_BULL | ema_cross, trend_alignment, macd_histogram | bb_reversion, stat_arb |
| TRENDING_BEAR | ema_cross (short), macd_histogram | rsi_threshold |
| RANGE_BOUND | rsi_threshold, bb_reversion, stat_arb_zscore | ema_cross |
| HIGH_VOLATILITY | volatility_breakout, volume_confirmation | stat_arb |
| LOW_VOLATILITY | rsi_threshold, stat_arb_zscore | momentum |
| CRASH_EVENT | REDUCE ALL EXPOSURE | All except hedges |

---

## Critical Configuration (.env additions)

```bash
# Research Pipeline
ENABLE_RESEARCH_PIPELINE=true
RESEARCH_CYCLE_INTERVAL_SEC=300
RESEARCH_EVOLUTION_INTERVAL_SEC=3600
RESEARCH_MIN_SHARPE=1.20
RESEARCH_MIN_FITNESS=0.30
RESEARCH_N_CANDIDATES_PER_CYCLE=50
RESEARCH_PERIODS=260

# Signal Factory
SIGNAL_MIN_STRENGTH=0.15
SIGNAL_COOLDOWN_SEC=300
SIGNAL_MAX_PER_ASSET_CLASS=4

# Ensemble
ENSEMBLE_METHOD=regime_adaptive
ENSEMBLE_MIN_AGREEMENT=0.40

# Feature Lab
FEATURE_TIMEFRAMES=5m,15m,1h,1d
FEATURE_LOOKBACK=250

# Ray
RAY_NUM_CPUS=4
RAY_NUM_GPUS=0
```

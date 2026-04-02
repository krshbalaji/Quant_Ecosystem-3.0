# Quant Ecosystem 3.0 — Institutional Research Architecture
## Renaissance-Style Self-Evolving Alpha Pipeline

---

## 1. System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     QUANT ECOSYSTEM 3.0 — FULL ARCHITECTURE                 │
└─────────────────────────────────────────────────────────────────────────────┘

╔══════════════════════════════════════════════════════════════════════════════╗
║  LAYER 0: MARKET DATA & FEATURE PIPELINE                                     ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  ┌─────────────┐    ┌──────────────────┐    ┌────────────────────────────┐  ║
║  │ FyersBroker │───▶│ MarketDataEngine │───▶│ FeatureEngineeringEngine   │  ║
║  │ CoinSwitch  │    │ (OHLCV, Level2)  │    │  IndicatorLibrary (40+)    │  ║
║  │ YFinance    │    │ SymbolMapper     │    │  FeatureStore (LRU+Parquet) │  ║
║  └─────────────┘    │ CandleBuilder    │    └────────────────────────────┘  ║
║                     └──────────────────┘                │                   ║
║                              │                           ▼                   ║
║                     ┌────────────────┐    ┌────────────────────────────┐    ║
║                     │ ResearchDataset│    │ FactorDatasetBuilder       │    ║
║                     │ Builder        │    │ (40+ factors: mom, vol,    │    ║
║                     │ (OHLCV arrays) │    │  micro, cs-rank, beta)     │    ║
║                     └────────────────┘    └────────────────────────────┘    ║
╚══════════════════════════════════════════════════════════════════════════════╝
                                     │
                                     ▼
╔══════════════════════════════════════════════════════════════════════════════╗
║  LAYER 1: ALPHA GENOME (Genetic Strategy Generation)                         ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  ┌──────────────────────────────────────────────────────────────────────┐   ║
║  │                         GENOME PIPELINE                               │   ║
║  │                                                                        │   ║
║  │  AlphaGenePool ──▶ AlphaDNABuilder ──▶ AlphaMutationEngine           │   ║
║  │  (16 gene types    (6-slot DNA:         (tournament select,           │   ║
║  │   trend/momentum/  market_filter +       elite preserve,              │   ║
║  │   vol/reversion/   signal +              adaptive mutation rate)      │   ║
║  │   volume/stats)    entry + exit +                │                    │   ║
║  │                    risk + execution)   AlphaCrossoverEngine           │   ║
║  │                         │              (uniform/k-point/blend)       │   ║
║  │                         │                        │                    │   ║
║  │                         └──────────┬─────────────┘                   │   ║
║  │                                    ▼                                   │   ║
║  │                           Candidate DNA Pool                           │   ║
║  └────────────────────────────────────┬──────────────────────────────────┘   ║
╚════════════════════════════════════════│═════════════════════════════════════╝
                                         │
                                         ▼
╔══════════════════════════════════════════════════════════════════════════════╗
║  LAYER 2: DISTRIBUTED RESEARCH ENGINE (Ray Cluster)                          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  ┌──────────────────────────────────────────────────────────────────────┐   ║
║  │                    DISTRIBUTED BACKTEST GRID                           │   ║
║  │                                                                        │   ║
║  │  DistributedResearchEngine                                             │   ║
║  │       │                                                                │   ║
║  │       ├── ResearchWorker[0] (Ray) ──▶ _quick_backtest (vectorised)    │   ║
║  │       ├── ResearchWorker[1] (Ray) ──▶ _quick_backtest (vectorised)    │   ║
║  │       ├── ResearchWorker[2] (Ray) ──▶ _quick_backtest (vectorised)    │   ║
║  │       └── ResearchWorker[N] (Ray) ──▶ _quick_backtest (vectorised)    │   ║
║  │                                                                        │   ║
║  │  ResearchPipelineManager orchestrates:                                 │   ║
║  │    Stage 0: Data fetch    → ResearchDatasetBuilder                     │   ║
║  │    Stage 1: DNA generate  → AlphaGenePool + AlphaDNABuilder            │   ║
║  │    Stage 2: Backtest      → Ray workers (parallel)                     │   ║
║  │    Stage 3: Track         → ExperimentTracker                          │   ║
║  │    Stage 4: Promote       → StrategyRegistry (SHADOW stage)            │   ║
║  │    Stage 5: Evolve        → Mutation + Crossover on top-10             │   ║
║  │                                                                        │   ║
║  │  ExperimentTracker: full lineage (genome → metrics → promotion)        │   ║
║  │  ResearchScheduler: time-based + regime-triggered research             │   ║
║  └────────────────────────────────────┬──────────────────────────────────┘   ║
╚════════════════════════════════════════│═════════════════════════════════════╝
                                         │ promoted strategies
                                         ▼
╔══════════════════════════════════════════════════════════════════════════════╗
║  LAYER 3: SIGNAL FACTORY                                                     ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  ┌──────────────────────┐   ┌──────────────────────┐   ┌────────────────┐  ║
║  │ SignalGeneratorEngine│──▶│ SignalFilterEngine    │──▶│SignalQuality   │  ║
║  │                      │   │                      │   │Engine          │  ║
║  │ FeatureStore + DNA   │   │ Regime gate          │   │ IC, turnover,  │  ║
║  │ → RawSignal per      │   │ Drawdown filter      │   │ decay tests    │  ║
║  │   (symbol × strat)   │   │ Correlation block    │   │ Overfitting    │  ║
║  │ Ray: parallel by     │   │ Min-strength gate    │   │ detection      │  ║
║  │ symbol batch         │   └──────────────────────┘   └────────────────┘  ║
║  └──────────────────────┘                                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
                                         │ filtered RawSignals
                                         ▼
╔══════════════════════════════════════════════════════════════════════════════╗
║  LAYER 4: META ALPHA ENGINE (Ensemble & Regime)                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  ┌───────────────────┐   ┌──────────────────────┐   ┌──────────────────┐   ║
║  │ RegimeDetection   │──▶│ AlphaCombination     │──▶│ EnsembleSignal   │   ║
║  │ Engine            │   │ Engine               │   │ Engine           │   ║
║  │                   │   │                      │   │                  │   ║
║  │ 7 regimes:        │   │ IC-weighted          │   │ CS-Z normalise   │   ║
║  │ TRENDING/RANGING/ │   │ Mean/Rank/PCA        │   │ IC adaptive wt   │   ║
║  │ HIGH_VOL/LOW_VOL/ │   │ combination          │   │ Vol adjustment   │   ║
║  │ BREAKOUT/REVERT/  │   │ → MetaSignal per     │   │ → OrderSignal    │   ║
║  │ CRISIS            │   │   symbol             │   │   with size_hint │   ║
║  │                   │   │                      │   │                  │   ║
║  │ Hurst + ADX +     │   │ Agreement rate       │   │ Ray: parallel    │   ║
║  │ Vol + Momentum    │   │ filtering            │   │   by timeframe   │   ║
║  └───────────────────┘   └──────────────────────┘   └──────────────────┘   ║
╚══════════════════════════════════════════════════════════════════════════════╝
                                         │ OrderSignals
                                         ▼
╔══════════════════════════════════════════════════════════════════════════════╗
║  LAYER 5: PORTFOLIO & EXECUTION                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  OrderSignal → CapitalAllocator → PortfolioConstructor → ExecutionPlanner   ║
║                     │                    │                      │            ║
║              Risk Parity          Correlation              Slippage Est.    ║
║              Kelly Sizing         Diversification           TWAP/VWAP       ║
║              Drawdown Guard       Max Concentration         Order Router     ║
║                                                                              ║
║  RiskEngine → BlackSwanGuard → SafetyGovernor → KillSwitch                  ║
║                                                             │                ║
║                                                    Broker (Fyers/Zerodha)   ║
╚══════════════════════════════════════════════════════════════════════════════╝
                                         │
                                         ▼
╔══════════════════════════════════════════════════════════════════════════════╗
║  LAYER 6: STRATEGY LIFECYCLE (Survival + Evolution)                          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  PAPER ──▶ SHADOW ──▶ LIVE ──▶ [DECAY_RETIRED / REPLACED]                  ║
║                                                                              ║
║  ShadowEngine → PromotionEvaluator → SurvivalEngine → DecayDetector         ║
║                         │                                      │             ║
║                  ResearchPipelineManager ◀──── StrategyReplacementMgr       ║
║                  (auto-generates replacements)                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
                                         │
                                         ▼
╔══════════════════════════════════════════════════════════════════════════════╗
║  LAYER 7: CONTROL & REPORTING                                                ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  TelegramController ─────▶ MasterOrchestrator ◀───── WebDashboard           ║
║  (signed audit trail)              │                 (cockpit UI)            ║
║                          EODReport │ InstitutionalPDF                        ║
║                          AdaptiveLearning → RegimePerformanceAnalyzer        ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## 2. Module Dependency Flow

```
ResearchDatasetBuilder
  └── MarketDataEngine (raw OHLCV)
  └── SyntheticGBM (fallback)

FactorDatasetBuilder
  └── ResearchDatasetBuilder (OHLCV arrays)
  └── compute_momentum_factors()
  └── compute_risk_factors()
  └── compute_technical_factors()
  └── compute_microstructure_factors()
  └── compute_cs_factors()              ← cross-sectional

IndicatorLibrary
  └── numpy vectorised (no pandas dependency)

FeatureEngineeringEngine
  └── MarketDataEngine
  └── IndicatorLibrary
  └── FeatureStore (LRU + parquet)

AlphaGenePool
  └── 16 gene templates (trend/momentum/vol/reversion/volume/statistical)
  └── JSON persistence (data/gene_pool/)

AlphaDNABuilder
  └── AlphaGenePool (gene selection)
  └── 6-slot DNA: market_filter → signal → entry → exit → risk → execution

AlphaMutationEngine
  └── GenomeMutator (low-level)
  └── AlphaGenePool (fitness feedback)
  └── PopulationStats (adaptive mutation rate)

AlphaCrossoverEngine
  └── GenomeCrossbreeder (low-level)
  └── Uniform / K-point / Family-aware / Blend modes

ResearchPipelineManager
  └── AlphaGenePool + AlphaDNABuilder (Stage 1: generate)
  └── ResearchDatasetBuilder (Stage 0: data)
  └── _quick_backtest() via Ray (Stage 2: evaluate)
  └── ExperimentTracker (Stage 3: track)
  └── StrategyRegistry.register() (Stage 4: promote → SHADOW)
  └── AlphaMutationEngine + AlphaCrossoverEngine (Stage 5: evolve)

DistributedResearchEngine
  └── ResearchPipelineManager (orchestration)
  └── ResearchWorker (Ray actor pool)
  └── RegimeDetectionEngine (regime tagging)

SignalGeneratorEngine
  └── FeatureStore (feature snapshots)
  └── _evaluate_strategy_dna() (pure function)
  └── Ray remote tasks (parallel symbol × strategy)

SignalFilterEngine
  └── RawSignal from SignalGeneratorEngine
  └── RegimeSnapshot (regime gate)
  └── Risk state (drawdown filter)

SignalQualityEngine
  └── Filtered signals
  └── IC computation, turnover, decay tests

RegimeDetectionEngine
  └── FeatureStore (cross-symbol features)
  └── Hurst + ADX + BB + Vol signals
  └── Temporal smoothing (window=5)

AlphaCombinationEngine
  └── RawSignals (multiple alpha sources)
  └── SignalQualityEngine (IC weighting)
  └── IC-weighted / PCA / rank combination

EnsembleSignalEngine
  └── MetaSignals from AlphaCombinationEngine
  └── RegimeSnapshot from RegimeDetectionEngine
  └── ICTracker (rolling IC per family)
  └── CS-Z normalisation
  └── Ray remote tasks (parallel by timeframe)
  └── → OrderSignal to ExecutionRouter
```

---

## 3. New Files — Where to Place Them

```
quant_ecosystem/
├── feature_lab/                          ✅ COMPLETE
│   ├── feature_engineering_engine.py    (390L) Orchestrates feature computation
│   ├── feature_store.py                 (223L) LRU + parquet cache
│   └── indicator_library.py             (417L) 40+ vectorised indicators
│
├── alpha_genome/                         ✅ COMPLETE
│   ├── alpha_gene_pool.py               (340L) 16 gene templates + pool CRUD
│   ├── alpha_dna_builder.py             (290L) 6-slot DNA assembly
│   ├── alpha_mutation_engine.py         (229L) Population-level evolution
│   ├── alpha_crossover_engine.py        (274L) Uniform/k-point/blend crossover
│   ├── genome_generator.py              (88L)  Low-level gene generation
│   ├── genome_mutator.py                (88L)  Low-level parameter mutation
│   ├── genome_crossbreeder.py           (42L)  Low-level gene recombination
│   ├── genome_evaluator.py              (134L) Fitness evaluation
│   └── genome_library.py               (93L)  Genome persistence
│
├── signal_factory/                       ✅ COMPLETE
│   ├── signal_generator_engine.py       (326L) DNA → RawSignal (Ray parallel)
│   ├── signal_filter_engine.py          (274L) Regime + quality gates
│   └── signal_quality_engine.py         (345L) IC, decay, overfitting tests
│
├── meta_alpha_engine/                    ✅ COMPLETE
│   ├── regime_detection_engine.py       (409L) 7-regime classifier
│   ├── alpha_combination_engine.py      (231L) IC-weighted signal combination
│   └── ensemble_signal_engine.py        (284L) CS-Z + vol-adj → OrderSignal
│
├── research_orchestrator/               ✅ COMPLETE
│   ├── research_pipeline_manager.py     (378L) Full genome→promote pipeline
│   ├── experiment_tracker.py            (271L) MLflow-style run tracking
│   └── research_scheduler.py            (282L) Time + regime-triggered runs
│
├── data_layer/                           ✅ COMPLETE
│   ├── research_dataset_builder.py      (303L) OHLCV fetching + caching
│   └── factor_dataset_builder.py        (380L) 40+ factor computation ← NEW
│
├── research/
│   └── distributed_research_engine.py   (327L) Ray worker pool ← UPGRADED
│
└── core/
    └── system_factory.py                (273L) Full wiring of all modules ← PATCHED
```

---

## 4. Code Modifications Required in Existing Modules

### A. `system_factory.py` — PATCHED (see above)
- Added imports for all 6 new module clusters
- All new engines wrapped in try/except (graceful degradation)
- Added to System container with descriptive attribute names
- Wired `research_pipeline.system` and `distributed_research.system`

### B. `distributed_research_engine.py` — UPGRADED
Before: 13-line stub calling `alpha_factory.evolve()`
After: Full production engine with:
- Ray actor pool (`ResearchWorker`)
- Async + threaded background run modes
- Auto-detects regime from `regime_engine.last_snapshot()`
- `DistributedAlphaGrid` backward-compat alias

### C. `alpha_evolution_engine.py` — Integration note
The existing `evolution/alpha_evolution_engine.py` is superseded by:
- `AlphaMutationEngine` (alpha_genome/) for parameter evolution
- `AlphaCrossoverEngine` (alpha_genome/) for gene recombination
- `ResearchPipelineManager` for full lifecycle

To keep backward compatibility, no changes required — both engines coexist.

### D. `master_orchestrator.py` — Recommended additions
Add to `_run_institutional_cycle()`:
```python
# Refresh regime snapshot
regime_eng = getattr(system, "regime_engine", None)
if regime_eng and feature_store:
    universe_features = feature_store.get_universe_snapshot()
    regime_snapshot = regime_eng.classify(universe_features)
    state.market_regime = regime_snapshot.dominant_regime

# Generate signals via new pipeline
signal_gen = getattr(system, "signal_generator", None)
ensemble   = getattr(system, "ensemble_engine", None)
if signal_gen and ensemble and regime_snapshot:
    raw_signals = signal_gen.generate_all(
        symbols=market_data.symbols,
        strategies=strategy_registry.get_live_dnas(),
        regime=regime_snapshot.dominant_regime,
    )
    meta_signals  = alpha_combinator.combine(raw_signals)
    order_signals = ensemble.ensemble(meta_signals, regime_snapshot)
    # Filter and route actionable signals
    for order in order_signals:
        if order.is_actionable():
            router.route(order)
```

---

## 5. Scaling to 1,000+ Strategies Per Day

### Current bottleneck analysis
| Component | Time/eval | Parallelism | Throughput |
|-----------|-----------|-------------|------------|
| DNA generation | <1ms | single-thread | ~100K/s |
| Quick backtest | ~5ms | Ray workers | ~800/min on 8 cores |
| Signal eval | ~0.5ms | Ray batches | ~12K/min |
| Promotion check | <0.1ms | trivial | bottleneck-free |

### To hit 1,000 strategies/day (minimum viable):
```
1,000 strategies / day
= 42 strategies / hour
= ~70 evaluations / hour (assuming 60% pass initial filter)
= 1.2 evaluations / minute

→ Single worker can handle this comfortably.
```

### To hit 10,000+ strategies/day:
```
10,000 / day = 700 / hour = 12 / minute
→ Need 2-3 Ray workers at full CPU (each eval ~5ms × 5 price series = 25ms)
→ 1 worker = 60,000ms / 25ms = 2,400 evals/hour
→ 1 worker easily handles 10K/day
```

### Architecture levers for scaling:
1. **Increase `n_candidates`** in `ResearchPipelineManager.run_research_cycle()`
   - Default 200, set to 1000+ for intensive runs
2. **Increase `n_workers`** in `DistributedResearchEngine`
   - Set to `os.cpu_count()` for max throughput
3. **Run research continuously** via `distributed_research.run_in_thread(interval_sec=300)`
4. **Expand price universe** in `ResearchDatasetBuilder` to include more symbols
   - More symbols → better cross-validation → fewer false positives
5. **Use Ray cluster** (multi-machine) by setting `ray.init(address="auto")`
6. **Pre-compute feature store** — call `FeatureEngineeringEngine.refresh()` on startup
7. **Reduce backtest window** for initial screening (use 100 bars), full backtest only for survivors

### Recommended production settings:
```python
# system_factory.py
research_pipeline = ResearchPipelineManager(
    promotion_criteria=PromotionCriteria(min_sharpe=1.8),  # higher bar
    use_ray=True,
)
distributed_research = DistributedResearchEngine(
    n_workers=8,        # match CPU cores
    batch_size=50,      # larger batches = less Ray overhead
    use_ray=True,
)

# Start continuous research in background thread:
distributed_research.start()
distributed_research.run_in_thread(interval_sec=300, n_candidates=500)
```

---

## 6. Performance Improvements

### A. Feature computation
- **Current**: per-symbol sequential in `FeatureEngineeringEngine`
- **Improvement**: Add Ray task per symbol batch in `refresh()` method
- **Gain**: 4-8× speedup on symbol universe

### B. Indicator library
- **Current**: EMA uses Python for-loop
- **Improvement**: Replace with `numba.jit` or `scipy.signal.lfilter`
- **Gain**: 10-50× for EMA, 3-5× for ATR/Bollinger

### C. Gene evaluation
- **Current**: `_evaluate_gene_signal()` uses Python dict lookups
- **Improvement**: Pre-compile gene evaluation to numpy vectorised ops
- **Gain**: 5-10× for batch evaluation

### D. Backtest engine
- **Current**: `_quick_backtest()` uses Python loops for EMA
- **Improvement**: Full vectorised using `np.convolve` or `pandas_ta`
- **Gain**: 3-5× per backtest

### E. Feature store
- **Current**: JSON-based disk store
- **Improvement**: Replace with `parquet` (already supported) + memory-map
- **Gain**: 10× read speed, 5× write speed

### F. Cross-sectional operations
- **Current**: Python dict comprehensions
- **Improvement**: Convert universe to pandas DataFrame for vectorised ops
- **Gain**: 3-10× for 50+ symbol universe

---

## 7. requirements.txt (Production)

```
# Core
numpy>=1.24.0
pandas>=2.0.0
scipy>=1.11.0

# Distributed
ray[default]>=2.9.0

# Broker
fyers-apiv3>=3.1.0
python-dotenv>=1.0.0
requests>=2.31.0

# Data
yfinance>=0.2.36
aiohttp>=3.9.0

# Persistence
pyarrow>=14.0.0

# ML/Stats
scikit-learn>=1.3.0

# Logging
loguru>=0.7.0

# Reporting
reportlab>=4.0.0
matplotlib>=3.7.0

# Optional: performance
# numba>=0.58.0         ← 10-50× indicator speedup
# pandas-ta>=0.3.14b    ← drop-in TA library
```

---

## 8. Known Issues & Fixes

| Issue | Status | Fix |
|-------|--------|-----|
| `core_momentum_v1` DECAY_RETIRED but stage=LIVE | 🔴 Active | Run `StrategyLifecycleManager.enforce_retirement()` |
| alpha_scanner `non_deployable: true` | 🔴 Active | Set to false in strategy_registry.json |
| 30 NO_SIGNAL cycles | 🔴 Active | Fixed by enabling alpha_scanner + new signal pipeline |
| Negative expectancy in lab strategies | 🟡 Monitor | Review microstructure cost model in SignalQualityEngine |
| requests.txt missing deps | 🔴 Active | Replace with requirements.txt above |
| Duplicate module paths | 🟡 Low | Consolidate risk_engine.py / telegram_controller.py |
| Diversity engine too restrictive | 🟡 Low | Increase `category_limit` in diversity_engine.py |


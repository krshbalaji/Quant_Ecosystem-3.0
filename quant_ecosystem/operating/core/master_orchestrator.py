import asyncio
from datetime import datetime
from itertools import count
import inspect
import logging
import time

from quant_ecosystem.core.runtime_state import RuntimeState

from quant_ecosystem.operating.control.telegram_control_center import TelegramControlCenter
from quant_ecosystem.operating.core.health.health_check import HealthCheck
from quant_ecosystem.operating.core.persistence.runtime_store import RuntimeStore
from quant_ecosystem.operating.core.scheduler import Scheduler
from quant_ecosystem.operating.core.strategy_lifecycle_manager import StrategyLifecycleManager
from quant_ecosystem.operating.core.strategy_portfolio_manager import StrategyPortfolioManager
from quant_ecosystem.operating.core.shutdown_handler import get_shutdown_handler, request_shutdown
from quant_ecosystem.operating.intelligence.adaptation_engine import AdaptationEngine
from quant_ecosystem.operating.intelligence.evolution_engine import EvolutionEngine
from quant_ecosystem.operating.intelligence.global_intelligence_engine import GlobalIntelligenceEngine
from quant_ecosystem.operating.intelligence.learning_engine import LearningEngine
from quant_ecosystem.operating.intelligence.recursive_engine import RecursiveEngine
from quant_ecosystem.operating.intelligence.research_engine import ResearchEngine
from quant_ecosystem.operating.intelligence.self_awareness_engine import SelfAwarenessEngine
from quant_ecosystem.operating.agents.ecosystem_coordinator import EcosystemCoordinator
from quant_ecosystem.operating.agents.agents import (
    ResearchAgent, StrategyAgent, PortfolioAgent, RiskAgent,
    ExecutionAgent, AwarenessAgent, RecursiveAgent
)
from quant_ecosystem.operating.network.network_node import NetworkNode
from quant_ecosystem.operating.network.network_manager import NetworkManager
from quant_ecosystem.operating.network.network_integrator import NetworkIntegrator
from quant_ecosystem.operating.market.market_universe_manager import MarketUniverseManager
from quant_ecosystem.operating.risk.portfolio_engine import PortfolioEngine
from quant_ecosystem.operating.reporting.eod.eod_report import EODReport
from quant_ecosystem.operating.risk.black_swan_guard import BlackSwanGuard
from quant_ecosystem.operating.risk.safety_layer import SafetyLayer
from quant_ecosystem.operating.risk.survival_playbook import SurvivalPlaybook
from quant_ecosystem.operating.risk.dynamic_risk_scaler import get_dynamic_risk_scaler
from quant_ecosystem.operating.strategy_bank.strategy_evaluator import StrategyEvaluator

logger = logging.getLogger(__name__)


class MasterOrchestrator:

    def __init__(self, system_or_router, runtime_state: RuntimeState = None):
        # Define global markets
        self.markets = {
            "FX": ["FX:USDINR", "FX:EURUSD"],
            "EQUITY": ["NSE:NIFTY", "NSE:RELIANCE"],
            "CRYPTO": ["BTCUSDT", "ETHUSDT"]
        }
        
        # Support both direct System container or ExecutionRouter with a
        # .system attribute, while always exposing engines via self.system.
        self.system = getattr(system_or_router, "system", system_or_router)
        self.router_ref = getattr(system_or_router, "execution_router", None)
        self.router = system_or_router
        self.market_data = getattr(self.system, "market_data", None)
        configured_cycles = int(getattr(getattr(self.system, "config", None), "runtime_cycles", 0) or 0)
        self.cycles = configured_cycles
        self.runtime_state = runtime_state or RuntimeState()
        self.state = self.runtime_state
        self.scheduler = Scheduler()
        self.health_check = HealthCheck()
        self.adaptation_engine = AdaptationEngine()
        

        # Prefer router-provided intelligence engine to ensure market_data is wired.
        self.intelligence_engine = getattr(
            self.system,
            "global_intelligence_engine",
            None,
        ) or GlobalIntelligenceEngine(config=getattr(self.system, "config", None))

        self.market_data = getattr(self.system, "market_data", None)
        self.learning_engine = LearningEngine()
        self.evolution_engine = EvolutionEngine()
        self.portfolio_engine = PortfolioEngine()
        self.self_awareness_engine = SelfAwarenessEngine()
        self.recursive_engine = RecursiveEngine()
        self.research_engine = ResearchEngine()

        # Initialize multi-agent ecosystem
        risk_engine = getattr(self.system, "risk_engine", None)
        execution_router = getattr(self.system, "execution_router", None)
        
        self.agents_dict = {
            "research": ResearchAgent(self.research_engine),
            "strategy": StrategyAgent(self.evolution_engine),
            "portfolio": PortfolioAgent(self.portfolio_engine),
            "risk": RiskAgent(risk_engine),
            "execution": ExecutionAgent(execution_router),
            "awareness": AwarenessAgent(self.self_awareness_engine),
            "recursive": RecursiveAgent(self.recursive_engine),
        }
        self.ecosystem_coordinator = EcosystemCoordinator(self.agents_dict)

        # Initialize Digital Intelligence Network
        node_id = getattr(getattr(self.system, "config", None), "network_node_id", "node_main_001")
        node_type = getattr(getattr(self.system, "config", None), "network_node_type", "general")
        
        self.network_node = NetworkNode(node_id, node_type)
        self.network_manager = NetworkManager(network_name="QE_Ecosystem_Network")
        self.network_integrator = NetworkIntegrator(self.network_node, self.network_manager, self)
        
        # Register this node in the network manager
        self.network_manager.nodes[node_id] = self.network_node
        self.network_manager.nodes_by_type[node_type].append(node_id)

        if hasattr(self.intelligence_engine, "set_market_data"):
            self.intelligence_engine.set_market_data(self.market_data)

        self.strategy_evaluator = StrategyEvaluator()
        self.strategy_portfolio = StrategyPortfolioManager()
        self.strategy_lifecycle = StrategyLifecycleManager()
        self.universe = MarketUniverseManager()
        self.reporter = EODReport()
        self.runtime_store = RuntimeStore()
        self.safety = SafetyLayer()
        self.black_swan = BlackSwanGuard()
        self.survival = SurvivalPlaybook()
        self.control_center = TelegramControlCenter(runtime_state=self.runtime_state)
        self._started = False
        self._background_tasks = set()
        if hasattr(self.system, "state") and self.system.state is not None:
            self.system.state.runtime_state = self.runtime_state

        if hasattr(self.system, "runtime_state"):
            self.system.runtime_state = self.runtime_state

        # Wire router reference for external stop control
        if hasattr(self.system, "execution_router") and self.system.execution_router is not None:
            self.system.execution_router.runtime_state = self.runtime_state
            self.system.execution_router.portfolio_engine = self.portfolio_engine

        # Ensure router gets portfolio engine as well
        setattr(system_or_router, "portfolio_engine", self.portfolio_engine)

        setattr(self.system, "orchestrator", self)


    async def _run_market_cycle(self, router, symbol, market, strategy, market_intelligence, regime, market_bias):
        """Run intelligence + execution cycle for specific symbol/strategy combination."""
        try:
            # Get symbol-specific intelligence
            intel = market_intelligence.get(symbol, {})
            confidence = intel.get("confidence", 0.3)
            price = intel.get("latest_price", 0.0)

            # Check correlation control (simple version)
            if self._check_correlation_overlap(symbol, market, strategy):
                return (strategy, {"status": "SKIP", "reason": "CORRELATION_OVERLAP", "symbol": symbol})

            # Check market-specific exposure
            market_exposure = self.portfolio_engine.get_market_exposure(market)
            market_limit = 0.3 * self.portfolio_engine.capital  # 30% per market
            if market_exposure > market_limit:
                return (strategy, {"status": "SKIP", "reason": f"MARKET_EXPOSURE_{market}", "symbol": symbol})

            # Build strategy-specific signal
            signal = None
            try:
                strategy_fn = None
                if getattr(router, "strategy_engine", None) and hasattr(router.strategy_engine, "registry"):
                    strategy_fn = router.strategy_engine.registry.get(strategy)
                if callable(strategy_fn):
                    market_context = {
                        "symbol": symbol,
                        "price": price,
                        "regime": regime,
                        "confidence": confidence,
                        "market": market,
                    }
                    candidate_signal = strategy_fn(market_context) or {}
                    if isinstance(candidate_signal, dict):
                        candidate_signal["strategy_id"] = strategy
                        candidate_signal["strategy"] = strategy
                        signal = candidate_signal
                else:
                    signal = {
                        "symbol": symbol,
                        "strategy_id": strategy,
                        "strategy": strategy,
                        "side": "BUY",
                        "confidence": confidence,
                        "trade_type": "AUTONOMOUS",
                        "price": price,
                        "qty": 1,
                        "regime": regime,
                        "market": market,
                    }
            except Exception as exc:
                logger.warning("[orchestrator] strategy building failed for %s on %s: %s", strategy, symbol, exc)
                return (strategy, {"status": "SKIP", "reason": f"STRATEGY_BUILD_ERROR: {exc}", "symbol": symbol})

            if not signal:
                return (strategy, {"status": "SKIP", "reason": "NO_SIGNAL", "symbol": symbol})

            # Execute trade
            try:
                async with router.execution_lock:
                    r = await router.execute(signal=signal, market_bias=market_bias, regime=regime)
                    r["symbol"] = symbol
                    r["market"] = market
            except Exception as exc:
                logger.exception("[orchestrator] execution failure for %s on %s: %s", strategy, symbol, exc)
                r = {"status": "SKIP", "reason": f"EXECUTION_ERROR: {exc}", "symbol": symbol, "market": market}

            return (strategy, r)

        except Exception as e:
            logger.error(f"[MARKET CYCLE ERROR] {symbol}/{strategy}: {e}")
            return (strategy, {"status": "ERROR", "reason": str(e), "symbol": symbol})

    def _check_correlation_overlap(self, symbol, market, strategy):
        """Simple correlation control - reduce overlap if same direction signals."""
        # Advanced version would check actual correlation matrix
        # For now, just allow all combinations
        return False

    def _apply_cross_market_signals(self, market_intelligence):
        """Apply cross-market signal logic to adjust allocations."""
        adjustments = {}
        
        # Example: if USDINR rising AND NIFTY falling, increase FX allocation, reduce equity
        fx_price = None
        equity_price = None
        fx_trend = 0.0
        equity_trend = 0.0
        
        for symbol, intel in market_intelligence.items():
            if symbol == "FX:USDINR":
                fx_price = intel.get("latest_price", 0.0)
                fx_trend = intel.get("trend_strength", 0.0)
            elif symbol == "NSE:NIFTY":
                equity_price = intel.get("latest_price", 0.0)
                equity_trend = intel.get("trend_strength", 0.0)
        
        if fx_price and equity_price:
            # Cross-market signal: FX up + Equity down = increase FX, reduce equity
            if fx_trend > 0.01 and equity_trend < -0.01:
                adjustments["FX"] = 1.2  # 20% increase
                adjustments["EQUITY"] = 0.8  # 20% decrease
                print("[CROSS-MARKET SIGNAL] FX↑ + EQUITY↓ -> FX allocation ↑20%, EQUITY ↓20%")
            # Opposite signal: FX down + Equity up = reduce FX, increase equity  
            elif fx_trend < -0.01 and equity_trend > 0.01:
                adjustments["FX"] = 0.8
                adjustments["EQUITY"] = 1.2
                print("[CROSS-MARKET SIGNAL] FX↓ + EQUITY↑ -> FX allocation ↓20%, EQUITY ↑20%")
        
        return adjustments


    def stop(self):
        """Global stop control method."""
        try:
            if self.runtime_state and hasattr(self.runtime_state, "stop"):
                self.runtime_state.stop()
        except Exception:
            pass
        logger.info("🛑 Orchestrator stopping...")

    async def run(self, router, *args, **kwargs):
        try:
            print(f"[DEBUG] SYSTEM RUNNING: {self.runtime_state.is_running()}")
            if self.runtime_state and self.runtime_state.is_running():
                await self.start(router, *args, **kwargs)
        except Exception as exc:
            logger.exception("[orchestrator] run-loop exception: %s", exc)
        finally:
            await self._cancel_remaining_tasks()

    # ------------------------------------------------------------------
    # Institutional helpers
    # ------------------------------------------------------------------

    def _run_institutional_cycle(
        self,
        router,
        cycle_id: int,
        regime: str,
        market_bias: str,
        intelligence_report: dict,
    ):
        """
        Optional institutional pipeline:
        1) FeatureEngine update
        2) StrategyUniverse (registry) update and signals (research)
        3) AlphaCompetition rankings
        4) CapitalAllocator weights
        5) PerformanceStore left for trade-based updates
        """
        system = self.system

        feature_engine = getattr(system, "feature_engine", None)
        if feature_engine and hasattr(feature_engine, "refresh"):
            feature_engine.refresh()

        # Strategy universe is loaded into StrategyRegistry at startup,
        # so there is no additional work required here to "load" it.

        alpha_comp = getattr(system, "alpha_competition", None)
        allocator = getattr(system, "capital_allocator", None)
        performance_store = getattr(system, "performance_store", None)

        rankings = None
        if alpha_comp and hasattr(alpha_comp, "evaluate"):
            rankings = alpha_comp.evaluate()

        allocation = {}
        if allocator and rankings is not None:
            metrics_map = (
                performance_store.get_all_metrics() if performance_store else {}
            )
            allocation = allocator.allocate(metrics_map)

        # At this stage allocations are advisory; ExecutionRouter sizing
        # remains governed by RiskEngine and portfolio constraints.
        if allocation:
            print(f"CapitalAllocator Weights: {allocation}")

    async def start(self, router, git_sync=None, auto_push_end=True, auto_tag_end=True):
        if self._started:
            logger.warning("start() called more than once; ignoring duplicate start request.")
            return
        self._started = True
        print("Quant Ecosystem 3.0 booting...")
        self.scheduler.start_day()
        mode = str(
            getattr(
                getattr(router, "state", None),
                "trading_mode",
                getattr(getattr(router, "config", None), "mode", "PAPER"),
            )
        ).upper()
        environment = str(getattr(getattr(router, "config", None), "environment", "DEV")).upper()
        data_mode = str(getattr(getattr(router, "config", None), "data_mode", "SYNTHETIC")).upper()
        logger.info("🔥 SYSTEM MODE: %s", mode)
        logger.info("🧭 ENVIRONMENT: %s | DATA MODE: %s", environment, data_mode)

        if hasattr(self.system, "market_data"):
            starter = getattr(self.system.market_data, "start", None)
            if callable(starter):
                started = starter()
                if asyncio.iscoroutine(started):
                    self._track_task(asyncio.create_task(started), "market_data.start")

        self._safe_start_component(self.system.alpha_competition, ["evaluate", "run"], "alpha_competition")
        self._safe_start_component(self.system.strategy_discovery, ["discover"], "strategy_discovery")
        self._safe_start_component(self.system.capital_intelligence, ["evaluate", "run"], "capital_intelligence")
        self._safe_start_component(self.system.alpha_evolution, ["evolve", "run"], "alpha_evolution")

        health = self.health_check.run(router=router)
        if mode == "LIVE" and not health.get("broker_connected", False):
            print("Health check failed: broker not connected. Aborting session.")
            return
        if mode == "PAPER":
            print("PAPER mode health gate: broker connectivity requirement skipped.")

        if getattr(router, "execution_router", None):
            router.execution_router.start_execution_loop()

        if router.telegram:
            sent = router.telegram.send_startup_ping()
            if sent:
                print("Telegram startup alert sent.")
            else:
                print("Telegram startup alert not sent (check token/chat id).")

        if router.strategy_engine:
            if hasattr(router.strategy_engine, "reload"):
                router.strategy_engine.reload()
            strategy_reports = []
            engine_strategies = getattr(router.strategy_engine, "strategies", None)
            if engine_strategies:
                strategy_reports = self.strategy_evaluator.evaluate(engine_strategies)
                strategy_reports = self._apply_lifecycle(strategy_reports)

            bank_engine = getattr(router, "strategy_bank_engine", None)
            if bank_engine and getattr(bank_engine, "enabled", False):
                strategy_reports = bank_engine.ingest_reports(strategy_reports)

            portfolio_plan = self.strategy_portfolio.build_portfolio(strategy_reports)
            strategy_reports = portfolio_plan["reports"]
            parliament = getattr(router, "lifecycle_parliament", None)
            bank_engine = getattr(router, "strategy_bank_engine", None)

            if parliament and bank_engine:

                for row in strategy_reports:

                    votes = row.get("_lifecycle_votes", [])

                    final_stage = parliament.decide_stage(
                        strategy_id=row.get("id"),
                        proposals=votes
                    )

                    row["stage"] = bank_engine.governor.decide_stage(
                        row=row,
                        candidate_stage=final_stage
                    )

                    row.pop("_lifecycle_votes", None)
            if hasattr(router.strategy_engine, "apply_policy"):
                router.strategy_engine.apply_policy(strategy_reports)
            top = strategy_reports[:3]
            print(f"Strategy evaluation top-3: {top}")
            active_ids = list(getattr(router.strategy_engine, "active_ids", []) or [])
            if not active_ids and hasattr(router.strategy_engine, "_get_live_strategies"):
                try:
                    active_ids = list((router.strategy_engine._get_live_strategies() or {}).keys())
                except Exception:
                    active_ids = []
            print(f"Active strategy ids: {active_ids}")
            if bank_engine and getattr(bank_engine, "enabled", False):
                active_bank_ids = []
                if hasattr(bank_engine, "get_active_strategies"):
                    active_bank_ids = list(bank_engine.get_active_strategies() or [])
                elif hasattr(bank_engine, "get_eligible_strategies"):
                    active_bank_ids = list(bank_engine.get_eligible_strategies() or [])
                allocation_snapshot = {}
                if hasattr(bank_engine, "get_allocation"):
                    allocation_snapshot = {
                        sid: bank_engine.get_allocation(sid)
                        for sid in active_bank_ids
                    }
                print(f"Strategy bank allocations: {allocation_snapshot}")
            if getattr(router, "strategy_manager", None):
                all_ids = list(active_ids or [])
                if not all_ids and engine_strategies:
                    all_ids = list(engine_strategies.keys())
                router.strategy_manager.sync_registry(all_ids)
        else:
            strategy_reports = []

        intelligence_report = self.intelligence_engine.analyze()
        self._refresh_intelligence_context(router, intelligence_report)
        detected = self._detect_and_broadcast_regime(router, intelligence_report)
        if detected:
            intelligence_report["regime_advanced"] = detected.get("regime", intelligence_report.get("regime_advanced"))
        market_bias = intelligence_report.get("bias", "NEUTRAL")
        regime_advanced = intelligence_report.get("regime_advanced", intelligence_report.get("regime", "LOW_VOLATILITY"))
        regime = self._map_regime_to_execution(regime_advanced)
        print("Global intelligence:", intelligence_report)

        bank_engine = getattr(router, "strategy_bank_engine", None)
        if bank_engine and getattr(bank_engine, "enabled", False):
            strategy_reports = bank_engine.ingest_reports(strategy_reports, intelligence_report=intelligence_report)
            if hasattr(router.strategy_engine, "apply_policy"):
                router.strategy_engine.apply_policy(strategy_reports)
        selector_allocator = self._run_selector_allocator(router, regime_advanced)
        if selector_allocator:
            print(f"Selector/Allocator: {selector_allocator}")
        diversity_report = self._run_strategy_diversity(router)
        if diversity_report:
            print(f"StrategyDiversity: {diversity_report}")
        survival_engine_report = self._run_strategy_survival(router)
        if survival_engine_report:
            print(f"StrategySurvival: {survival_engine_report}")
        meta_decision = self._run_meta_brain(
            router=router,
            regime_advanced=regime_advanced,
            strategy_reports=strategy_reports,
            mutated_candidates=[],
        )
        if meta_decision:
            print(f"MetaBrain: {meta_decision}")

        router.symbols = self._resolve_active_symbols(router, regime_advanced)
        router.execution_lock = getattr(router, "execution_lock", None) or asyncio.Lock()
        command_task = self._track_task(asyncio.create_task(self._poll_telegram_commands(router)), "telegram_command_poll")
        alpha_task = self._start_alpha_scanner(router)
        portfolio_ai_task = self._start_portfolio_ai(router)
        strategy_lab_task = self._start_strategy_lab_autorun(router)
        event_signal_task = self._start_event_signal_engine(router)
        market_pulse_task = self._start_market_pulse_engine(router)
        event_orchestrator_task = self._start_event_driven_orchestrator(router)
        dashboard_task = self._start_dashboard_service(router)
        cockpit_task = self._start_cockpit_service(router)
        shadow_task = self._start_shadow_trading_engine(router)
        alpha_genome_task = self._start_alpha_genome_engine(router)
        alpha_factory_task = self._start_alpha_factory(router)
        global_brain_task = self._start_global_market_brain(router)
        adaptive_batch_interval = max(
            1,
            int(getattr(router.config, "adaptive_learning_batch_interval_cycles", 10)),
        )
        if getattr(router, "adaptive_learning_engine", None):
            router._adaptive_last_trade_index = len(getattr(router.state, "trade_history", []) or [])
            print(f"Adaptive learning enabled: batch_interval_cycles={adaptive_batch_interval}")
        if getattr(router, "cognitive_controller", None):
            cc_interval = max(0.5, float(getattr(router.config, "cognitive_control_interval_sec", 2.0)))
            print(f"Cognitive control enabled: interval={cc_interval}s")

        if hasattr(self.system, "alpha_discovery") and self.system.alpha_discovery:
            self._safe_start_component(self.system.alpha_discovery, ["discover", "run"], "alpha_discovery")

        if hasattr(self.system, "alpha_grid") and self.system.alpha_grid:
            if hasattr(self.system.alpha_grid, "run_cycle"):
                self.system.alpha_grid.run_cycle()
            elif hasattr(self.system.alpha_grid, "run"):
                self.system.alpha_grid.run()

        if hasattr(self.system, "market_data"):
            get_snapshot = getattr(self.system.market_data, "get_snapshot", None)
            if callable(get_snapshot):
                _ = self.system.market_data.get_snapshot()
            else:
                _ = self.system.market_data.get_market_data()

        try:
            shutdown = get_shutdown_handler()
            i = 0
            while self.runtime_state.is_running():
                if not self.runtime_state.is_running():
                    break
                print(f"[DEBUG] SYSTEM RUNNING: {self.runtime_state.is_running()}")
                i += 1
                if self.cycles > 0 and i > self.cycles:
                    break
                if not self.runtime_state.is_running():
                    break

                # Fail-safe: prevent runaway loop
                if i > 100000:
                    logger.warning("Loop safety break triggered at cycle %d", i)
                    break
                    
                cycle_started = time.perf_counter()
                print(f"Cycle {i}")
                
                # Safety sleep to prevent CPU hogging
                await asyncio.sleep(0.2)
                
                # Update dynamic risk scaler with current equity
                current_equity = float(getattr(router.state, "equity", 100_000.0) or 100_000.0)
                dynamic_scaler = get_dynamic_risk_scaler()
                risk_status = dynamic_scaler.update_cycle(current_equity, cycle_num=i)
                if risk_status.get("kill_switch"):
                    logger.critical("🚨 Dynamic risk scaler: KILL SWITCH ACTIVE - halting trading")
                    if router.state:
                        router.state.trading_halted = True
                if i % 50 == 0:
                    logger.info(
                        "Risk Status: DD=%s RiskScale=%.2f Anomaly=%s",
                        risk_status.get("dd_stage"),
                        risk_status.get("risk_scale"),
                        risk_status.get("anomaly_reason")
                    )
                
                refresh_every = max(1, int(getattr(router.config, "intelligence_refresh_cycles", 5)))
                if i > 1 and (i % refresh_every == 0):
                    # 🔥 FORCE DATA FLOW IN ORCHESTRATOR LOOP
                    symbol = "FX:USDINR"

                    try:
                        for _ in range(10):
                            if self.market_data and hasattr(self.market_data, "get_price_sync"):
                                self.market_data.get_price_sync(symbol)
                    except Exception as e:
                        print(f"[DATA WARMUP ERROR] {e}")

                    intelligence_report = self.intelligence_engine.analyze()
                    self._refresh_intelligence_context(router, intelligence_report)
                    detected = self._detect_and_broadcast_regime(router, intelligence_report)
                    if detected:
                        intelligence_report["regime_advanced"] = detected.get("regime", intelligence_report.get("regime_advanced"))
                    market_bias = intelligence_report.get("bias", market_bias)
                    regime_advanced = intelligence_report.get("regime_advanced", intelligence_report.get("regime", regime_advanced))
                    regime = self._map_regime_to_execution(regime_advanced)
                    print("Global intelligence:", intelligence_report)
                    selector_allocator = self._run_selector_allocator(router, regime_advanced)
                    if selector_allocator:
                        print(f"Selector/Allocator: {selector_allocator}")
                    diversity_report = self._run_strategy_diversity(router)
                    if diversity_report:
                        print(f"StrategyDiversity: {diversity_report}")
                    survival_engine_report = self._run_strategy_survival(router)
                    if survival_engine_report:
                        print(f"StrategySurvival: {survival_engine_report}")
                    meta_decision = self._run_meta_brain(
                        router=router,
                        regime_advanced=regime_advanced,
                        strategy_reports=strategy_reports,
                        mutated_candidates=[],
                    )
                    if meta_decision:
                        print(f"MetaBrain: {meta_decision}")

                router.symbols = self._resolve_active_symbols(router, regime_advanced)
                if getattr(router, "execution_router", None):
                    router.execution_router.symbols = list(router.symbols or [])
                self._prime_symbol_data(router)

                # Institutional loop hook
                try:
                    self._run_institutional_cycle(
                        router=router,
                        cycle_id=i,
                        regime=regime,
                        market_bias=market_bias,
                        intelligence_report=intelligence_report,
                    )
                except Exception as exc:
                    logger.exception("[orchestrator] institutional cycle failure: %s", exc)

                # MULTI-MARKET INTELLIGENCE COLLECTION (always run)
                market_intelligence = {}
                for market, symbols in self.markets.items():
                    for symbol in symbols:
                        try:
                            intel = self.intelligence_engine.analyze(symbol=symbol)
                            market_intelligence[symbol] = intel
                            print(f"[INTELLIGENCE] {symbol}: confidence={intel.get('confidence', 0):.3f} volatility={intel.get('volatility', 0):.4f}")
                        except Exception as e:
                            print(f"[INTELLIGENCE ERROR] {symbol}: {e}")

                # Update portfolio allocation with market intelligence
                top_strategies = self.evolution_engine.select_top(top_n=3)
                if top_strategies and market_intelligence:
                    # Apply cross-market signals
                    cross_market_adjustments = self._apply_cross_market_signals(market_intelligence)
                    
                    allocations = self.portfolio_engine.allocate(
                        {strat: self.evolution_engine.get_score(strat) for strat in top_strategies},
                        market_intelligence
                    )
                    
                    # Apply cross-market adjustments to allocations
                    if cross_market_adjustments:
                        for strategy, symbol_allocs in allocations.items():
                            for symbol, capital in symbol_allocs.items():
                                market = "UNKNOWN"
                                if symbol.startswith("FX:"):
                                    market = "FX"
                                elif symbol.startswith("NSE:"):
                                    market = "EQUITY"
                                elif "USDT" in symbol or "BTC" in symbol or "ETH" in symbol:
                                    market = "CRYPTO"
                                
                                if market in cross_market_adjustments:
                                    adjustment = cross_market_adjustments[market]
                                    allocations[strategy][symbol] = capital * adjustment
                    
                    print(f"[PORTFOLIO ALLOCATION] {allocations}")

                # Check global risk limit
                total_exposure = self.portfolio_engine.get_total_exposure()
                global_limit = 0.5 * self.portfolio_engine.capital
                if total_exposure > global_limit:
                    print(f"[GLOBAL RISK] Exposure {total_exposure:.0f} > {global_limit:.0f} limit - blocking trades")
                    continue

                # MULTI-MARKET PARALLEL EXECUTION
                results = []
                if top_strategies:
                    # Parallel execution across markets and symbols
                    tasks = []
                    for market, symbols in self.markets.items():
                        for symbol in symbols:
                            for strat in top_strategies:
                                task = self._run_market_cycle(router, symbol, market, strat, market_intelligence, regime, market_bias)
                                tasks.append(task)

                    # Execute all tasks concurrently
                    if tasks:
                        try:
                            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                            for result in batch_results:
                                if isinstance(result, Exception):
                                    logger.error(f"[PARALLEL EXECUTION ERROR] {result}")
                                else:
                                    results.append(result)
                        except Exception as e:
                            logger.error(f"[PARALLEL EXECUTION FAILED] {e}")
                else:
                    # Fallback single execution
                    try:
                        async with router.execution_lock:
                            r = await router.execute(market_bias=market_bias, regime=regime)
                    except Exception as exc:
                        logger.exception("[orchestrator] execution failure: %s", exc)
                        r = {"status": "SKIP", "reason": f"EXECUTION_ERROR: {exc}"}
                    results.append((None, r))

                # Process results and track market performance
                market_performance = {"FX": 0.0, "EQUITY": 0.0, "CRYPTO": 0.0}
                executed_trades = []

                for strat, result in results:
                    loop_symbol = result.get("symbol") or "NONE"
                    loop_market = result.get("market") or "UNKNOWN"
                    loop_strategy = strat or result.get("strategy_id") or "NONE"
                    logger.info(
                        "[loop] symbol=%s market=%s regime=%s strategy=%s status=%s",
                        loop_symbol,
                        loop_market,
                        regime,
                        loop_strategy,
                        result.get("status", "UNKNOWN"),
                    )

                    if result.get("status") == "TRADE":
                        executed_trades.append(result)
                        trade_pnl = float(result.get("pnl", 0.0) or 0.0)
                        market_performance[loop_market] = market_performance.get(loop_market, 0.0) + trade_pnl

                # Print market performance summary
                if executed_trades:
                    print(f"[MARKET PERFORMANCE] {market_performance}")
                    for result in executed_trades:
                        print(
                            "Executed |",
                            result.get("strategy_id", "UNKNOWN"),
                            result.get("symbol", "UNKNOWN"),
                            result.get("market", "UNKNOWN"),
                            result.get("side", "UNKNOWN"),
                            "qty",
                            result.get("qty", 0),
                            "PnL",
                            result.get("pnl", 0.0),
                        )

                # Process first result for backward compatibility (for risk scaler, learning, etc.)
                if results:
                    strat, result = results[0]  # Use first result for legacy processing
                    trade_pnl = 0.0  # Initialize
                    if result.get("status") == "TRADE":
                        # Record trade result for dynamic risk scaler anomaly detection
                        trade_pnl = float(result.get("pnl", 0.0) or 0.0)
                        dynamic_scaler.record_trade_result(trade_pnl, cycle_num=i)

                        # Record for learning engine
                        try:
                            self.learning_engine.record_trade({
                                "symbol": result.get("symbol"),
                                "pnl": trade_pnl,
                                "confidence": float(result.get("confidence", 0.0) or 0.0),
                            })
                            print("[LEARNING ENGINE ACTIVE]", self.learning_engine.evaluate())
                        except Exception as e:
                            logger.warning("Learning engine record_trade failed: %s", e)

                        learning_stats = self.learning_engine.evaluate()
                        win_rate = float(learning_stats.get("win_rate", 0.0))
                        if getattr(router, "risk_engine", None) and hasattr(router.risk_engine, "max_trade_risk"):
                            base_risk = float(getattr(router.risk_engine, "max_trade_risk", 0.0) or 0.0)
                            if win_rate > 0.6:
                                router.risk_engine.max_trade_risk = min(1.0, base_risk * 1.2)
                            elif win_rate < 0.4:
                                router.risk_engine.max_trade_risk = max(0.01, base_risk * 0.8)

                    strategy_id = str(result.get("strategy_id") or result.get("strategy") or "unknown")
                    self.evolution_engine.register(strategy_id)
                    self.evolution_engine.record(strategy_id, trade_pnl)

                if i % 10 == 0:
                    top_strategies = self.evolution_engine.select_top(top_n=3)
                    print("[EVOLUTION] top_strategies:", top_strategies)

                    # SELF-AWARENESS: Observe, diagnose, and adjust
                    if self.self_awareness_engine.should_observe(i):
                        try:
                            # Collect system state
                            learning_stats = self.learning_engine.evaluate()
                            strategy_scores = self.evolution_engine.strategy_scores or {}
                            portfolio_allocations = self.portfolio_engine.allocations or {}

                            # Compute drawdown (simplified)
                            current_equity = float(getattr(router.state, "equity", 100_000.0) or 100_000.0)
                            peak_equity = float(getattr(router.state, "peak_equity", current_equity) or current_equity)
                            drawdown = (peak_equity - current_equity) / peak_equity if peak_equity > 0 else 0.0

                            # Get market volatility from recent intelligence
                            avg_volatility = 0.0
                            if hasattr(self, 'intelligence_engine') and self.intelligence_engine:
                                # Use last known volatility or default
                                avg_volatility = 0.03  # Default, could be improved

                            state = {
                                "win_rate": learning_stats.get("win_rate", 0.0),
                                "avg_pnl": learning_stats.get("avg_win", 0.0),
                                "drawdown": drawdown,
                                "active_strategies": len([s for s in strategy_scores.values() if s and s > 0]),
                                "total_trades": len(getattr(router.state, "trade_history", []) or []),
                                "volatility": avg_volatility,
                            }

                            # Observe system state
                            self.self_awareness_engine.observe(state)

                            # Diagnose issues
                            issues = self.self_awareness_engine.diagnose()

                            # Generate suggestions
                            actions = self.self_awareness_engine.suggest(issues)

                            # Log self-awareness activity
                            print("[SELF-AWARENESS]")
                            print(f"  Issues detected: {issues}")
                            print(f"  Suggested actions: {actions}")

                            # Apply safe adjustments
                            if actions:
                                self.self_awareness_engine.apply(router, actions)
                                print(f"  Adjustments applied: {len(actions)} changes made")

                            # RECURSIVE AI: Observe self-awareness decisions
                            performance_metric = learning_stats.get("avg_win", 0.0)
                            self.recursive_engine.observe(issues, actions, performance_metric)

                            # Evaluate effectiveness and adjust rules if needed
                            if self.recursive_engine.should_evaluate(i):
                                status = self.recursive_engine.evaluate()
                                if status:
                                    print("[RECURSIVE AI]")
                                    print(f"  Status: {status}")

                                    # Adjust SelfAwarenessEngine rules based on evaluation
                                    self.recursive_engine.adjust_rules(self.self_awareness_engine, status)

                        except Exception as e:
                            logger.warning(f"Self-awareness cycle failed: {e}")
                            print(f"[SELF-AWARENESS ERROR] {e}")

                    # RESEARCH AI: Generate and test market hypotheses
                    if self.research_engine.should_research(i):
                        try:
                            # Use market intelligence as test data
                            research_report = self.research_engine.run_research_cycle(market_intelligence)

                            print("[RESEARCH AI]")
                            print(f"  Hypothesis: {research_report['hypothesis']}")
                            print(f"  Score: {research_report['result_score']:.4f}")
                            print(f"  Signals: {research_report['signals']}")
                            print(f"  Validated: {research_report['validated_count']}")
                            print(f"  Knowledge base: {research_report['knowledge_base_size']} insights")

                            # Export discovered knowledge for use by other engines
                            knowledge = self.research_engine.export_knowledge()
                            if knowledge.get("top_insights"):
                                print(f"  Top insight: {knowledge['top_insights'][0]['hypothesis']}")

                        except Exception as e:
                            logger.warning(f"Research cycle failed: {e}")
                            print(f"[RESEARCH AI ERROR] {e}")

                    # 🤖 MULTI-AGENT ECOSYSTEM ORCHESTRATION
                    # Run all agents through coordinated cycle for independent yet synchronized intelligence
                    try:
                        print("[MULTI-AGENT ECOSYSTEM] Starting 7-agent coordination cycle...")
                        
                        # Initialize shared context with market and system state
                        base_context = {
                            "cycle_id": i,
                            "market_data": market_intelligence,
                            "learning_stats": self.learning_engine.evaluate(),
                            "strategy_scores": self.evolution_engine.strategy_scores or {},
                            "top_strategies": self.evolution_engine.select_top(top_n=3),
                            "portfolio": self.portfolio_engine.allocations or {},
                            "router_state": {
                                "equity": float(getattr(router.state, "equity", 100_000.0) or 100_000.0),
                                "peak_equity": float(getattr(router.state, "peak_equity", 100_000.0) or 100_000.0),
                                "trades": len(getattr(router.state, "trade_history", []) or []),
                            },
                            "regime": regime,
                            "bias": market_bias,
                        }
                        
                        # Run coordinated 7-agent cycle: Research→Strategy→Portfolio→Risk→Execution→Awareness→Recursive
                        coordinator_context = self.ecosystem_coordinator.run_cycle(base_context)
                        
                        # Display ecosystem health and results
                        ecosystem_status = self.ecosystem_coordinator.get_agent_status()
                        print("[ECOSYSTEM STATUS]")
                        print(f"  Active agents: {len(ecosystem_status)} | Execution count: {sum(a.get('execution_count', 0) for a in ecosystem_status.values())}")
                        
                        for agent_name, agent_info in ecosystem_status.items():
                            if agent_info.get("execution_count", 0) > 0:
                                print(f"    {agent_name}: executed {agent_info.get('execution_count', 0)}x, errors: {agent_info.get('error_count', 0)}")
                        
                        # Display coordinator summary
                        summary = self.ecosystem_coordinator.get_context_summary(coordinator_context)
                        if summary:
                            print("[AGENT INSIGHTS]")
                            if "research_insights" in summary and summary["research_insights"]:
                                print(f"  Research: {len(summary['research_insights'])} hypotheses generated")
                            if "strategy_selection" in summary and summary["strategy_selection"]:
                                print(f"  Strategy: {summary['strategy_selection'].get('count', 0)} candidates evaluated")
                            if "portfolio_allocation" in summary and summary["portfolio_allocation"]:
                                print(f"  Portfolio: {len(summary['portfolio_allocation'])} symbols allocated")
                        
                    except Exception as e:
                        logger.warning(f"Multi-agent ecosystem cycle failed: {e}")
                        print(f"[ECOSYSTEM ERROR] {e}")

                    # 🌐 DIGITAL INTELLIGENCE NETWORK INTEGRATION
                    # Broadcast local knowledge and consume external insights
                    try:
                        # Broadcast phase: Share insights with peers
                        if self.network_integrator.should_broadcast(i):
                            print("[DIGITAL NETWORK] Broadcasting cycle...")
                            
                            # Broadcast research insights
                            research_broadcast = self.network_integrator.broadcast_research_insights(i, self.research_engine)
                            
                            # Broadcast strategy performance
                            strategy_broadcast = self.network_integrator.broadcast_strategy_performance(i, self.evolution_engine)
                            
                            # Broadcast performance metrics
                            metrics_broadcast = self.network_integrator.broadcast_performance_metrics(
                                i,
                                self.learning_engine,
                                router.state
                            )
                            
                            if research_broadcast or strategy_broadcast or metrics_broadcast:
                                print(f"[NETWORK] Research:{research_broadcast} Strategy:{strategy_broadcast} Metrics:{metrics_broadcast}")

                        # Consume phase: Use external knowledge to improve decisions
                        if self.network_integrator.should_consume(i):
                            print("[DIGITAL NETWORK] Consuming external insights...")
                            
                            # Get external insights
                            external_data = self.network_integrator.consume_external_insights(i)
                            
                            # Apply external insights to strategy selection
                            if external_data.get("external_insights"):
                                local_win_rate = self.learning_engine.evaluate().get("win_rate", 0.5)
                                enhanced_scores = self.network_integrator.apply_network_insights_to_strategy(
                                    i,
                                    external_data["external_insights"],
                                    self.evolution_engine.strategy_scores or {},
                                    local_win_rate
                                )
                                
                                # Store enhanced scores for use in next strategy selection
                                if enhanced_scores != self.evolution_engine.strategy_scores:
                                    logger.debug(f"[NETWORK] Strategy scores enhanced by external insights")

                            # Apply external metrics to portfolio allocation
                            if external_data.get("external_metrics"):
                                current_allocs = self.portfolio_engine.allocations or {}
                                adjusted_allocs = self.network_integrator.apply_network_insights_to_portfolio(
                                    i,
                                    external_data["external_metrics"],
                                    current_allocs
                                )
                                
                                if adjusted_allocs != current_allocs:
                                    logger.debug(f"[NETWORK] Portfolio allocation adjusted by external metrics")

                            # Log network integration status
                            integration_status = self.network_integrator.get_integration_status()
                            print(f"[NETWORK STATUS] Peers:{integration_status['peers_connected']} Memory:{integration_status['shared_memory_size']} Decisions:{integration_status['network_influenced_decisions']}")

                    except Exception as e:
                        logger.warning(f"Digital network integration failed: {e}")
                        print(f"[NETWORK ERROR] {e}")

                    # Portfolio allocation from evolution scores
                    scores = {
                        s: self.evolution_engine.score(s)
                        for s in self.evolution_engine.strategy_scores
                    }
                    allocations = self.portfolio_engine.allocate(scores)
                    print("[PORTFOLIO ALLOCATION]", allocations)

                    # Hang allocation into router for execution router usage
                    setattr(router, "portfolio_engine", self.portfolio_engine)

                    self.evolution_engine.evolve_population(router)

                else:
                    print("Skipped | Reason:", result.get("reason", "UNKNOWN"))

                self.runtime_store.write_cycle(
                    cycle_id=i,
                    result=result,
                    state=router.state,
                )
                self._update_runtime_memory(router=router, cycle_id=i, intelligence_report=intelligence_report, result=result)
                if router.telegram and (i % max(1, int(getattr(router.config, "telegram_cycle_summary_interval", 5))) == 0):
                    summary_line = (
                        f"📡 Cycle {i} | Symbol: {loop_symbol} | Regime: {regime} | "
                        f"Status: {result.get('status', 'UNKNOWN')} | Equity: {round(float(getattr(router.state, 'equity', 0.0) or 0.0), 2)}"
                    )
                    router.telegram.send_message(summary_line)
                adaptive_report = self._run_adaptive_learning(
                    router=router,
                    result=result,
                    intelligence_report=intelligence_report,
                    cycle_id=i,
                    batch_interval_cycles=adaptive_batch_interval,
                )
                if adaptive_report:
                    print(f"AdaptiveLearning: {adaptive_report}")
                cognitive_report = self._run_cognitive_controller(
                    router=router,
                    regime_advanced=regime_advanced,
                )
                if cognitive_report:
                    print(f"CognitiveControl: {cognitive_report}")
                safety_report = self._run_safety_governor(
                    router=router,
                    result=result,
                    intelligence_report=intelligence_report,
                    regime=regime,
                )
                if safety_report and safety_report.get("alert_level") != "NONE":
                    print(f"SafetyGovernor: {safety_report}")
                    if router.telegram:
                        router.telegram.send_message(
                            f"SafetyGovernor: {safety_report.get('alert_level')} | {safety_report.get('reason')}"
                        )
                    if safety_report.get("alert_level") == "EMERGENCY_STOP":
                        break

                if result.get("status") == "TRADE" and bank_engine and getattr(bank_engine, "enabled", False):
                    sid = str(result.get("strategy_id", ""))
                    if sid:
                        if getattr(router, "strategy_manager", None):
                            perf_log = self._load_json_file("storage/performance_log.json", default={})
                            router.strategy_manager.assess_performance(perf_log)
                        strategy_trades = [
                            t for t in router.state.trade_history if str(t.get("strategy", "")) == sid
                        ]
                        closed = [t for t in strategy_trades if t.get("closed_trade")]
                        win_rate = (len([t for t in closed if float(t.get("realized_pnl", 0.0)) > 0]) / len(closed) * 100.0) if closed else 0.0
                        expectancy = 0.0
                        if closed:
                            expectancy = sum(float(t.get("realized_pnl", 0.0)) for t in closed) / len(closed)
                        bank_engine.update_performance(
                            sid,
                            {
                                "sample_size": len(strategy_trades),
                                "win_rate": round(win_rate, 4),
                                "expectancy": round(expectancy, 4),
                            },
                        )

                swan = self.black_swan.evaluate(
                    intelligence_report=intelligence_report,
                    snapshots=[],
                )
                if swan["action"] == "REDUCE_RISK":
                    router.risk_engine.set_trade_risk_pct(router.risk_engine.max_trade_risk * 0.9)
                    if router.telegram:
                        router.telegram.send_message(f"Black swan guard: {swan['reason']} -> risk reduced.")
                elif swan["action"] == "PAUSE":
                    router.stop_trading()
                    router.set_auto_mode(False)
                    if router.telegram:
                        router.telegram.send_message(f"Black swan guard: {swan['reason']} -> trading paused.")
                    break
                elif swan["action"] == "CLOSE_EXPOSURE":
                    self.control_center.execute("close_all", router)
                    router.stop_trading()
                    router.set_auto_mode(False)
                    if router.telegram:
                        router.telegram.send_message(f"Black swan guard: {swan['reason']} -> exposure closed.")
                    break

                survival_decision = self.survival.evaluate(router, result, intelligence_report)
                survival_msg = self.survival.apply(router, self.control_center, survival_decision)
                if survival_msg:
                    print("Survival:", survival_msg)
                    if router.telegram:
                        router.telegram.send_message(f"Survival: {survival_msg}")
                    if self.survival.mode == "PAUSED":
                        break

                if router.telegram:
                    router.telegram.update_dashboard(role=router.telegram._active_role)

                if router.telegram:
                    webhook_failover = router.telegram.watchdog_tick(router)
                    if webhook_failover:
                        print("Webhook failover:", webhook_failover)
                        break

                safe, reason = self.safety.evaluate_cycle(router, result)
                if not safe:
                    print("Safety halt:", reason)
                    if router.telegram:
                        router.telegram.send_message(f"Safety halt: {reason}")
                    break
                await asyncio.sleep(0.2)
        finally:
            self.stop()
            await self._shutdown_service_task(router, dashboard_task, "_dashboard_uvicorn_server", "dashboard")
            await self._shutdown_service_task(router, cockpit_task, "_cockpit_uvicorn_server", "cockpit")
            await self._cancel_task(command_task, "telegram_command_poll")
            await self._cancel_task(alpha_task, "alpha_scanner")
            await self._cancel_task(portfolio_ai_task, "portfolio_ai")
            await self._cancel_task(strategy_lab_task, "strategy_lab")
            await self._cancel_task(event_signal_task, "event_signal")
            await self._cancel_task(market_pulse_task, "market_pulse")
            await self._cancel_task(event_orchestrator_task, "event_orchestrator")
            await self._cancel_task(shadow_task, "shadow_trading")
            await self._cancel_task(alpha_genome_task, "alpha_genome")
            await self._cancel_task(alpha_factory_task, "alpha_factory")
            await self._cancel_task(global_brain_task, "global_market_brain")

        adaptation_report = self.adaptation_engine.apply(router.state, router.risk_engine)
        print(f"Adaptation: {adaptation_report}")

        if getattr(router, "outcome_memory", None):
            router.outcome_memory.update_from_trades(router.state.trade_history)

        mutation_engine = getattr(router, "mutation_engine", None)
        mutated = []
        if mutation_engine and getattr(mutation_engine, "enabled", False):
            mutated = mutation_engine.run_daily(strategy_reports)
            if mutated:
                print(f"Mutation engine accepted candidates: {len(mutated)}")
        meta_after_mutation = self._run_meta_brain(
            router=router,
            regime_advanced=regime_advanced,
            strategy_reports=strategy_reports,
            mutated_candidates=mutated,
        )
        if meta_after_mutation:
            print(f"MetaBrain(post-mutation): {meta_after_mutation}")

        self.reporter.generate(
            state=router.state,
            intelligence_report=intelligence_report,
            strategy_reports=strategy_reports,
            adaptation_report=adaptation_report,
        )
        performance_log = {}
        if getattr(router, "execution_router", None) and hasattr(router.execution_router, "_load_performance_log"):
            performance_log = router.execution_router._load_performance_log()
        if getattr(router, "self_learning_engine", None):
            learning = router.self_learning_engine.evaluate(performance_log=performance_log)
            setattr(router.state, "self_learning_report", learning)
        if getattr(router, "eod_report_engine", None):
            router.eod_report_engine.generate(
                state=router.state,
                performance_log=performance_log,
                lessons=list(getattr(router.state, "daily_lessons", []) or []),
            )
        if git_sync and auto_push_end:
            git_sync.push_on_end(create_eod_tag=auto_tag_end)
        print("Session complete")

    def _refresh_intelligence_context(self, router, intelligence_report):
        pre_market = {}
        if getattr(router, "pre_market_intelligence", None):
            try:
                pre_market = router.pre_market_intelligence.analyze(market_data=getattr(router, "market_data", None))
            except Exception:
                pre_market = {}

            # 🔥 FORCE MARKET DATA GENERATION (FINAL FIX — SAFE ACCESS)

            # 🔥 MARKET DATA WARMUP

            try:
                symbols = ["FX:USDINR"]

                for sym in symbols:
                    for _ in range(5):
                        self.market_data.get_price_sync(sym)

            except Exception as e:
                print(f"[DATA WARMUP ERROR] {e}")
                
        event_view = {}
        if getattr(router, "event_intelligence", None):
            try:
                event_view = router.event_intelligence.analyze()
            except Exception:
                event_view = {}
        strategy_ids = []
        if getattr(router, "strategy_engine", None) and hasattr(router.strategy_engine, "_get_live_strategies"):
            try:
                strategy_ids = list((router.strategy_engine._get_live_strategies() or {}).keys())
            except Exception:
                strategy_ids = []
        performance_log = {}
        if getattr(router, "execution_router", None) and hasattr(router.execution_router, "_load_performance_log"):
            performance_log = router.execution_router._load_performance_log()
        day_plan = {}
        if getattr(router, "day_planner", None):
            try:
                day_plan = router.day_planner.plan(
                    symbols=list(getattr(router, "symbols", []) or getattr(getattr(router, "market_data", None), "get_universe", lambda: [])()),
                    strategies=strategy_ids,
                    capital_intelligence=getattr(router, "capital_intelligence", None),
                    market_view=pre_market,
                    event_view=event_view,
                    performance_log=performance_log,
                )
            except Exception:
                day_plan = {}

        setattr(router.state, "pre_market_view", pre_market)
        setattr(router.state, "event_intelligence", event_view)
        setattr(router.state, "day_plan", day_plan)
        if isinstance(pre_market, dict):
            if not isinstance(pre_market, dict):
                pre_market = {}

            if not isinstance(intelligence_report, dict):
                intelligence_report = {
                    "bias": "NEUTRAL",
                    "latest_price": intelligence_report if isinstance(intelligence_report, (int, float)) else None
                }

            market_bias = pre_market.get("market_bias", intelligence_report.get("bias", "NEUTRAL"))

            print(f"[DEBUG] intelligence_report type: {type(intelligence_report)}")


            print(f"[DEBUG] pre_market type: {type(pre_market)}")

        else:
            market_bias = intelligence_report.get("bias", "NEUTRAL")
        setattr(router.state, "market_bias", market_bias)    
        setattr(router.state, "risk_mode", pre_market.get("risk_mode", "RISK_ON"))
        setattr(
            router.state,
            "system_thinking",
            {
                "regime": intelligence_report.get("regime_advanced", intelligence_report.get("regime", "LOW_VOLATILITY")),
                "market_bias": getattr(router.state, "market_bias", "NEUTRAL"),
                "risk_mode": getattr(router.state, "risk_mode", "RISK_ON"),
                "event_type": event_view.get("event_type", "NONE"),
                "day_plan": day_plan,
                "last_reason": getattr(router.state, "last_trade_explanation", "Awaiting setup"),
            },
        )
        if event_view.get("event_type") in {"WAR", "BLACK_SWAN"} or (
            pre_market.get("volatility") == "HIGH" and pre_market.get("risk_mode") == "RISK_OFF" and event_view.get("impact") == "HIGH"
        ):
            router.stop_trading()
            router.set_auto_mode(False)
            setattr(router.state, "daily_lessons", ["Trading halted by black swan protection."])

    async def _poll_telegram_commands(self, router):
        if not router.telegram:
            return

        while self.runtime_state.is_running():
            if not self.runtime_state.is_running():
                break
            commands = router.telegram.consume_webhook_events()
            for command, result in commands:
                cmd_lower = str(command).lower().strip()
                
                # Handle shutdown command
                if cmd_lower == "/stop_system":
                    logger.info("Stop command received via Telegram.")
                    router.telegram.send_message("🛑 System shutdown initiated. Cleaning up...")
                    if self.runtime_state and hasattr(self.runtime_state, "stop"):
                        self.runtime_state.stop()
                    request_shutdown("Telegram /stop_system command")
                    self.stop()
                    if getattr(router, "execution_router", None) and getattr(router.execution_router, "runtime_state", None):
                        router.execution_router.runtime_state.stop()
                    break
                
                # Handle other commands
                response = f"Command {command}: {result}"
                print(response)
                if not str(command).startswith("button:"):
                    router.telegram.send_message(response)
            
            await asyncio.sleep(1)

    def _apply_lifecycle(self, strategy_reports):
        out = []
        for report in strategy_reports:
            metrics = report.get("metrics", {})
            stage = self.strategy_lifecycle.assess(metrics=metrics, current_stage="candidate")
            mapped = self._stage_map(stage)
            out.append({**report, "stage": mapped})
        return out

    def _stage_map(self, stage):
        value = str(stage).lower()
        mapping = {
            "candidate": "REJECTED",
            "paper": "PAPER",
            "shadow": "PAPER_SHADOW",
            "live": "LIVE",
            "retired": "RETIRED",
        }
        return mapping.get(value, "REJECTED")

    def _safe_start_component(self, component, method_names, label):
        if not component:
            return
        for method_name in method_names:
            fn = getattr(component, method_name, None)
            if not callable(fn):
                continue
            try:
                sig = inspect.signature(fn)
                required = [
                    param
                    for param in sig.parameters.values()
                    if param.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
                    and param.default is inspect._empty
                ]
                if required:
                    logger.info(
                        "%s: skipped startup call for %s because it requires runtime parameters: %s",
                        label,
                        method_name,
                        [param.name for param in required],
                    )
                    return
            except Exception:
                pass
            try:
                result = fn()
                if asyncio.iscoroutine(result):
                    self._track_task(asyncio.create_task(result), f"{label}.{method_name}")
                return
            except TypeError as exc:
                logger.info("%s: skipped startup call for %s due to signature mismatch (%s)", label, method_name, exc)
                return
            except Exception as exc:
                print(f"{label}: startup call for {method_name} failed ({exc})")
                return

    def _detect_and_broadcast_regime(self, router, intelligence_report):
        ai_engine = getattr(router, "regime_ai_engine", None)
        timeframe_data = self._build_regime_timeframe_data(router)
        if not timeframe_data:
            return None
        extra = {
            "market_breadth": intelligence_report.get("market_breadth", 0.0),
            "vix": intelligence_report.get("vix"),
        }
        if ai_engine:
            state = ai_engine.detect_regime(timeframe_data=timeframe_data, extra_signals=extra)
            ai_engine.broadcast_regime(
                state,
                strategy_bank_layer=getattr(router, "strategy_bank_layer", None),
                strategy_selector=getattr(router, "strategy_selector", None),
                meta_strategy_brain=getattr(router, "meta_strategy_brain", None),
                capital_allocator_engine=getattr(router, "capital_allocator_engine", None),
                autonomous_controller=getattr(router, "autonomous_controller", None),
            )
            return state

        detector = getattr(router, "market_regime_detector", None)
        if not detector:
            return None
        state = detector.detect_regime(timeframe_data=timeframe_data, extra_signals=extra)
        detector.broadcast_regime(
            state,
            strategy_bank_layer=getattr(router, "strategy_bank_layer", None),
            autonomous_controller=getattr(router, "autonomous_controller", None),
        )
        return state

    def _build_regime_timeframe_data(self, router):
        if not getattr(router, "market_data", None):
            return {}
        symbols = list(getattr(router, "symbols", []) or [])
        if not symbols:
            symbols = ["NSE:NIFTY50-INDEX"]
        symbol = symbols[0]

        def make_tf(lookback, vol_base):
            if not hasattr(router.market_data, "get_close_series"):
                return {}
            close = router.market_data.get_close_series(symbol, lookback=lookback)
            if len(close) < 20:
                return {}
            high = [round(value * 1.0015, 6) for value in close]
            low = [round(value * 0.9985, 6) for value in close]
            volume = [vol_base + ((idx % 7) * (vol_base * 0.02)) for idx in range(len(close))]
            spread = [0.05 if "NSE:" in symbol else 0.0002 for _ in close]
            return {
                "close": close,
                "high": high,
                "low": low,
                "volume": volume,
                "spread": spread,
            }

        return {
            "5m": make_tf(80, 1000.0),
            "15m": make_tf(120, 1800.0),
            "1h": make_tf(160, 3000.0),
            "1d": make_tf(200, 5500.0),
        }

    def _map_regime_to_execution(self, regime_advanced):
        mapping = {
            "TRENDING_BULL": "TREND",
            "TRENDING_BEAR": "TREND",
            "RANGE_BOUND": "MEAN_REVERSION",
            "HIGH_VOLATILITY": "HIGH_VOLATILITY",
            "LOW_VOLATILITY": "LOW_VOLATILITY",
            "CRASH_EVENT": "CRISIS",
        }
        key = str(regime_advanced).upper()
        return mapping.get(key, "MEAN_REVERSION")

    def _run_selector_allocator(self, router, regime_advanced):
        selector = getattr(router, "strategy_selector", None)
        allocator = getattr(router, "capital_allocator_engine", None)
        if not selector or not allocator:
            return None

        try:
            selection = selector.select(
                market_regime=str(regime_advanced).upper(),
                risk_limits={"max_drawdown": 20.0, "min_profit_factor": 0.9, "min_sharpe": -2.0},
                capital_available_pct=100.0,
            )
            diagnostics = dict(selection.get("diagnostics", {}) or {})
            blocked_reasons = dict(diagnostics.get("blocked_reasons", {}) or {})
            candidate_ids = [
                str(row.get("id"))
                for row in list(selection.get("candidates", []) or [])
                if row.get("id")
            ]
            selected_ids = [
                str(row.get("id"))
                for row in list(selection.get("selected", []) or [])
                if row.get("id")
            ]
            router._selector_last_snapshot = {
                "regime": str(regime_advanced).upper(),
                "candidate_ids": candidate_ids,
                "selected_ids": selected_ids,
                "blocked_reasons": blocked_reasons,
                "candidate_count": int(diagnostics.get("candidate_count", len(candidate_ids)) or len(candidate_ids)),
                "selected_count": int(diagnostics.get("selected_count", len(selected_ids)) or len(selected_ids)),
                "tradeable_rows": int(diagnostics.get("tradeable_rows", 0) or 0),
                "total_rows": int(diagnostics.get("total_rows", 0) or 0),
            }
            allocation = allocator.rebalance(
                regime=str(regime_advanced).upper(),
                strategy_rows=selection.get("selected", []),
                capital_available_pct=100.0,
                current_drawdown_pct=float(getattr(router.state, "total_drawdown_pct", 0.0)),
            )
            return {
                "regime": str(regime_advanced).upper(),
                "active_ids": selection.get("activation", {}).get("active_ids", []),
                "activated": selection.get("activation", {}).get("activated", []),
                "deactivated": selection.get("activation", {}).get("deactivated", []),
                "candidate_count": router._selector_last_snapshot.get("candidate_count", 0),
                "selected_count": router._selector_last_snapshot.get("selected_count", 0),
                "blocked_count": len(router._selector_last_snapshot.get("blocked_reasons", {}) or {}),
                "alloc": allocation.get("allocation", {}),
                "rebalanced": allocation.get("rebalanced", False),
            }
        except Exception as exc:
            return {"regime": str(regime_advanced).upper(), "error": str(exc)}

    def _resolve_active_symbols(self, router, regime_advanced):
        try:
            if getattr(router.config, "enable_global_session_fallback", True):
                classes = self.universe.asset_classes_for_session()
            else:
                classes = ["stocks", "indices"]
            if hasattr(self.universe, "get_symbols"):
                symbols = self.universe.get_symbols(
                    asset_classes=classes,
                    regime=regime_advanced,
                    limit=8,
                )
            else:
                universe_symbols = getattr(self.universe, "symbols", [])
                if callable(universe_symbols):
                    symbols = universe_symbols(asset_classes=classes, regime=regime_advanced, limit=8)
                else:
                    symbols = list(universe_symbols or [])
            resolved = list(symbols or [])
            setattr(router.state, "active_symbols", resolved)
            return resolved
        except Exception as exc:
            logger.exception("[orchestrator] symbol resolution failure: %s", exc)
            return list(getattr(router, "symbols", []) or [])

    def _run_meta_brain(self, router, regime_advanced, strategy_reports, mutated_candidates):
        meta_brain = getattr(router, "meta_strategy_brain", None)
        if not meta_brain:
            return None
        try:
            decisions = meta_brain.evaluate_strategy_ecosystem(
                regime=str(regime_advanced).upper(),
                strategy_rows=strategy_reports,
                mutated_candidates=mutated_candidates,
                max_active=max(1, int(getattr(router.config, "meta_max_active_strategies", 5))),
            )
            return {
                "active": decisions.get("ACTIVE_STRATEGIES", []),
                "reduced": decisions.get("REDUCED_STRATEGIES", []),
                "retired": decisions.get("RETIRED_STRATEGIES", []),
                "promoted": decisions.get("PROMOTED_STRATEGIES", []),
            }
        except Exception as exc:
            return {"error": str(exc)}

    def _govern_activation(
        self,
        router,
        selector_result=None,
        diversity_result=None,
        survival_result=None,
    ):
        """
        CENTRAL STRATEGY ACTIVATION GOVERNOR

        This is the ONLY place allowed to change active strategy set.
        """

        selector = getattr(router, "strategy_selector", None)
        layer = getattr(router, "strategy_bank_layer", None)

        if not selector or not hasattr(selector, "activation_manager"):
            return

        try:
            rows = layer.registry_rows() if layer and hasattr(layer, "registry_rows") else []
            available_ids = [str(r.get("id")) for r in rows if r.get("id")]

            # 1️⃣ Selector recommendation
            recommended = []
            if selector_result:
                recommended = selector_result.get("recommended_ids", []) or []

            # 2️⃣ Diversity constraints
            if diversity_result:
                allowed = diversity_result.get("allowed", []) or []
                if allowed:
                    recommended = [sid for sid in recommended if sid in allowed]

            # 3️⃣ Survival retirements
            if survival_result:
                retired = survival_result.get("retired", []) or []
                recommended = [sid for sid in recommended if sid not in retired]

            # Safety fallback
            if not recommended and available_ids:
                recommended = available_ids[:1]


        except Exception:
            pass

    def _run_strategy_diversity(self, router):
        engine = getattr(router, "strategy_diversity_engine", None)
        if not engine:
            return None
        try:
            result = engine.run_cycle(
                strategy_bank_layer=getattr(router, "strategy_bank_layer", None),
                meta_strategy_brain=getattr(router, "meta_strategy_brain", None),
                portfolio_ai=getattr(router, "portfolio_ai_engine", None),
                max_active=max(1, int(getattr(router.config, "meta_max_active_strategies", 5))),
            )
            constraints = result.get("constraints", {})
            allowed_ids = constraints.get("allowed_ids", [])
            blocked_ids = constraints.get("blocked_ids", [])
            selector = getattr(router, "strategy_selector", None)
            if selector and hasattr(selector, "activation_manager"):
                try:
                    rows = []
                    layer = getattr(router, "strategy_bank_layer", None)
                    if layer and hasattr(layer, "registry_rows"):
                        rows = layer.registry_rows()
                    available_ids = [str(row.get("id")) for row in rows if row.get("id")]
                    return {
                        "allowed": allowed_ids,
                        "blocked": blocked_ids,
                        
                    }
                except Exception:
                    pass
            return {
                "allowed": allowed_ids,
                "blocked": blocked_ids,
                "updated": result.get("strategy_bank", {}).get("updated", 0),
            }
        except Exception as exc:
            return {"error": str(exc)}

    def _run_strategy_survival(self, router):
        engine = getattr(router, "strategy_survival_engine", None)
        if not engine:
            return None
        try:
            result = engine.run_cycle()
            # Keep selector activation aligned after retire/reduce/replace outcomes.
            
            return {
                "decaying": result.get("decaying", []),
                "reduced": result.get("reduced", []),
                "retired": result.get("retired", []),
                "replacements": result.get("replacements", []),
            }
        except Exception as exc:
            return {"error": str(exc)}

    def _start_alpha_scanner(self, router):
        scanner = getattr(router, "alpha_scanner", None)
        if not scanner:
            return None
        if not bool(getattr(router.config, "enable_alpha_scanner", False)):
            return None
        top_n = max(10, int(getattr(router.config, "alpha_scanner_top_n", 100)))
        interval = max(60, int(getattr(router.config, "alpha_scanner_interval_sec", 180)))
        scanner.cycle_interval_sec = interval
        print(f"Alpha scanner started: interval={interval}s top_n={top_n}")
        return self._track_task(asyncio.create_task(scanner.run_forever(top_n=top_n)), "alpha_scanner")

    def _start_portfolio_ai(self, router):
        engine = getattr(router, "portfolio_ai_engine", None)
        if not engine:
            return None
        if not bool(getattr(router.config, "enable_portfolio_ai", False)):
            return None
        interval = int(getattr(router.config, "portfolio_ai_interval_sec", 300))
        interval = max(300, min(600, interval))
        capital_pct = float(getattr(router.config, "portfolio_ai_capital_pct", 100.0))
        print(f"Portfolio AI started: interval={interval}s capital_pct={round(capital_pct, 2)}")
        return self._track_task(asyncio.create_task(self._run_portfolio_ai_loop(router, interval, capital_pct)), "portfolio_ai")

    async def _run_portfolio_ai_loop(self, router, interval_sec, capital_pct):
        engine = getattr(router, "portfolio_ai_engine", None)
        if not engine:
            return
        shutdown = get_shutdown_handler()
        while self.runtime_state.is_running():
            if not self.runtime_state.is_running():
                break
            regime = str(getattr(router.autonomous_controller, "last_regime", "RANGE_BOUND")).upper()
            try:
                outcome = engine.run_cycle(regime=regime, capital_pct=capital_pct)
                alloc = outcome.get("published", {}).get("allocations", {})
                print(f"PortfolioAI: regime={regime} allocations={alloc}")
            except Exception as exc:
                print(f"PortfolioAI error: {exc}")
            await asyncio.sleep(interval_sec)

    def _start_strategy_lab_autorun(self, router):
        controller = getattr(router, "strategy_lab_controller", None)
        if not controller:
            return None
        if not bool(getattr(router.config, "enable_strategy_lab_autorun", False)):
            return None

        interval = int(getattr(router.config, "strategy_lab_autorun_interval_sec", 900))
        interval = max(300, interval)
        generate_count = max(1, int(getattr(router.config, "strategy_lab_autorun_generate_count", 8)))
        variants_per_base = max(1, int(getattr(router.config, "strategy_lab_autorun_variants_per_base", 4)))
        periods = max(120, int(getattr(router.config, "strategy_lab_autorun_periods", 260)))
        print(
            "Strategy Lab autorun started: "
            f"interval={interval}s gen={generate_count} variants={variants_per_base} periods={periods}"
        )
        return self._track_task(
            asyncio.create_task(
                self._run_strategy_lab_loop(
                    router=router,
                    interval_sec=interval,
                    generate_count=generate_count,
                    variants_per_base=variants_per_base,
                    periods=periods,
                )
            ),
            "strategy_lab",
        )

    async def _run_strategy_lab_loop(self, router, interval_sec, generate_count, variants_per_base, periods):
        controller = getattr(router, "strategy_lab_controller", None)
        if not controller:
            return
        shutdown = get_shutdown_handler()
        while self.runtime_state.is_running():
            if not self.runtime_state.is_running():
                break
            try:
                outcome = controller.run_experiment(
                    generate_count=generate_count,
                    variants_per_base=variants_per_base,
                    periods=periods,
                )
                promoted = outcome.get("PROMOTED_STRATEGIES", [])
                validated = outcome.get("VALIDATED_STRATEGIES", [])
                print(
                    "StrategyLab: "
                    f"validated={len(validated)} promoted={len(promoted)} sandbox={outcome.get('sandbox_mode')}"
                )
            except Exception as exc:
                print(f"StrategyLab error: {exc}")
            await asyncio.sleep(interval_sec)

    def _start_event_signal_engine(self, router):
        engine = getattr(router, "event_signal_engine", None)
        if not engine:
            return None
        if not bool(getattr(router.config, "enable_event_signal_engine", False)):
            return None
        cooldown = max(1, int(getattr(router.config, "event_signal_engine_cooldown_sec", 20)))
        max_executes = max(0, int(getattr(router.config, "event_signal_engine_max_immediate_executes", 3)))
        # Poll faster than cooldown; cooldown governs event trigger frequency.
        poll_sec = max(1.0, min(5.0, cooldown / 4.0))
        print(
            "Event signal engine started: "
            f"cooldown={cooldown}s max_immediate_executes={max_executes} poll={poll_sec}s"
        )
        return self._track_task(asyncio.create_task(self._run_event_signal_loop(router, poll_sec=poll_sec)), "event_signal")

    async def _run_event_signal_loop(self, router, poll_sec):
        engine = getattr(router, "event_signal_engine", None)
        if not engine:
            return
        shutdown = get_shutdown_handler()
        while self.runtime_state.is_running():
            if not self.runtime_state.is_running():
                break
            try:
                regime = str(getattr(router.autonomous_controller, "last_regime", "MEAN_REVERSION")).upper()
                market_bias = "NEUTRAL"
                if hasattr(router, "_build_snapshots"):
                    snapshots = router._build_snapshots(regime=regime)
                else:
                    snapshots = []
                if snapshots:
                    async with router.execution_lock:
                        outcome = await engine.process_snapshots(
                            snapshots=snapshots,
                            router=router,
                            alpha_scanner=getattr(router, "alpha_scanner", None),
                            market_bias=market_bias,
                            regime=regime,
                            scanner_top_n=max(10, int(getattr(router.config, "alpha_scanner_top_n", 100))),
                        )
                    event_count = len(outcome.get("events", []))
                    executed = len(outcome.get("executed", []))
                    if event_count > 0:
                        print(f"EventSignal: events={event_count} executed={executed}")
            except Exception as exc:
                print(f"EventSignal error: {exc}")
            await asyncio.sleep(poll_sec)

    def _start_market_pulse_engine(self, router):
        engine = getattr(router, "market_pulse_engine", None)
        if not engine:
            return None
        if not bool(getattr(router.config, "enable_market_pulse_engine", False)):
            return None
        poll_sec = max(0.5, float(getattr(router.config, "market_pulse_poll_sec", 2.0)))
        print(f"Market pulse started: poll={poll_sec}s")
        return self._track_task(asyncio.create_task(self._run_market_pulse_loop(router, poll_sec=poll_sec)), "market_pulse")

    async def _run_market_pulse_loop(self, router, poll_sec):
        engine = getattr(router, "market_pulse_engine", None)
        if not engine:
            return
        shutdown = get_shutdown_handler()
        while self.runtime_state.is_running():
            if not self.runtime_state.is_running():
                break
            try:
                regime = str(getattr(router.autonomous_controller, "last_regime", "MEAN_REVERSION")).upper()
                snapshots = router._build_snapshots(regime=regime) if hasattr(router, "_build_snapshots") else []
                if snapshots:
                    events = engine.detect_events(snapshots)
                    if events:
                        published = engine.publish_events(
                            events=events,
                            event_bus=getattr(router, "event_bus", None),
                            signal_engine=getattr(router, "event_signal_engine", None),
                            strategy_selector=getattr(router, "strategy_selector", None),
                            execution_engine=router,
                            meta_strategy_brain=getattr(router, "meta_strategy_brain", None),
                        )
                        print(f"MarketPulse: events={len(events)} published={published}")
            except Exception as exc:
                print(f"MarketPulse error: {exc}")
            await asyncio.sleep(poll_sec)

    def _start_event_driven_orchestrator(self, router):
        orchestrator = getattr(router, "event_driven_orchestrator", None)
        if not orchestrator:
            return None
        if not bool(getattr(router.config, "enable_event_driven_engine", False)):
            return None
        print("Event-driven orchestrator started.")
        return self._track_task(asyncio.create_task(orchestrator.run_forever()), "event_driven_orchestrator")

    def _start_dashboard_service(self, router):
        cfg = getattr(router, "dashboard_service_config", {}) or {}
        if not bool(cfg.get("enabled", False)):
            return None
        host = str(cfg.get("host", "127.0.0.1"))
        port = int(cfg.get("port", 8090))
        interval = max(0.1, float(cfg.get("update_interval_sec", 0.25)))
        print(f"Dashboard service starting: http://{host}:{port} interval={interval}s")
        return self._track_task(
            asyncio.create_task(
                self._run_dashboard_service(router=router, host=host, port=port, interval=interval)
            ),
            "dashboard_service",
        )

    async def _run_dashboard_service(self, router, host, port, interval):
        try:
            from quant_ecosystem.operating.dashboard.dashboard_server import create_dashboard_app
            import uvicorn
        except Exception as exc:
            print(f"Dashboard service unavailable: {exc}")
            return
        app = create_dashboard_app(
            router_provider=lambda: router,
            update_interval_sec=interval,
        )
        server = uvicorn.Server(
            uvicorn.Config(
                app=app,
                host=host,
                port=int(port),
                log_level="warning",
         
            )
        )
        setattr(router, "_dashboard_uvicorn_server", server)
        try:
            await server.serve()
        except asyncio.CancelledError:
            server.should_exit = True
            raise
        except Exception as exc:
            print(f"Dashboard service error: {exc}")
        finally:
            setattr(router, "_dashboard_uvicorn_server", None)

    def _start_cockpit_service(self, router):
        cfg = getattr(router, "cockpit_service_config", {}) or {}
        if not bool(cfg.get("enabled", False)):
            return None
        host = str(cfg.get("host", "127.0.0.1"))
        port = int(cfg.get("port", 8091))
        interval = max(0.1, float(cfg.get("update_interval_sec", 0.25)))
        print(f"Cockpit service starting: http://{host}:{port} interval={interval}s")
        return self._track_task(
            asyncio.create_task(
                self._run_cockpit_service(
                    router=router,
                    host=host,
                    port=port,
                    interval=interval,
                    auth_token=str(cfg.get("auth_token", "")),
                )
            ),
            "cockpit_service",
        )

    async def _run_cockpit_service(self, router, host, port, interval, auth_token):
        try:
            from quant_ecosystem.research.cockpit.cockpit_server import create_cockpit_app
            import uvicorn
        except Exception as exc:
            print(f"Cockpit service unavailable: {exc}")
            return
        app = create_cockpit_app(
            router_provider=lambda: router,
            update_interval_sec=interval,
            auth_token=auth_token,
        )
        server = uvicorn.Server(
            uvicorn.Config(
                app=app,
                host=host,
                port=int(port),
                log_level="warning",
               
            )
        )
        setattr(router, "_cockpit_uvicorn_server", server)
        try:
            await server.serve()
        except asyncio.CancelledError:
            server.should_exit = True
            raise
        except Exception as exc:
            print(f"Cockpit service error: {exc}")
        finally:
            setattr(router, "_cockpit_uvicorn_server", None)

    def _start_shadow_trading_engine(self, router):
        engine = getattr(router, "shadow_trading_engine", None)
        if not engine:
            return None
        if not bool(getattr(router.config, "enable_shadow_trading", False)):
            return None
        interval = max(0.5, float(getattr(router.config, "shadow_trading_interval_sec", 2.0)))
        if getattr(router, "strategy_engine", None):
            try:
                engine.register_shadow_strategies(getattr(router.strategy_engine, "strategies", []))
            except Exception:
                pass
        print(f"Shadow trading started: interval={interval}s")
        return self._track_task(asyncio.create_task(self._run_shadow_trading_loop(router, interval_sec=interval)), "shadow_trading")

    async def _run_shadow_trading_loop(self, router, interval_sec):
        engine = getattr(router, "shadow_trading_engine", None)
        if not engine:
            return
        shutdown = get_shutdown_handler()
        while self.runtime_state.is_running():
            if not self.runtime_state.is_running():
                break
            try:
                regime = str(getattr(router.autonomous_controller, "last_regime", "MEAN_REVERSION")).upper()
                market_bias = "NEUTRAL"
                async with router.execution_lock:
                    outcome = engine.run_cycle(router=router, market_bias=market_bias, regime=regime)
                executed = int(outcome.get("executed", 0) or 0)
                promoted = len(list(outcome.get("promotions", []) or []))
                if executed > 0 or promoted > 0:
                    print(f"ShadowTrading: executed={executed} promoted={promoted}")
            except Exception as exc:
                print(f"ShadowTrading error: {exc}")
            await asyncio.sleep(interval_sec)

    def _run_safety_governor(self, router, result, intelligence_report, regime):
        engine = getattr(router, "safety_governor", None)
        if not engine:
            return None
        if not bool(getattr(router.config, "enable_safety_governor", False)):
            return None

        now = time.time()
        interval = max(0.2, float(getattr(router.config, "safety_governor_interval_sec", 2.0)))
        last_eval = float(getattr(router, "_safety_gov_last_eval_ts", 0.0) or 0.0)
        if last_eval > 0.0 and (now - last_eval) < interval:
            return None
        router._safety_gov_last_eval_ts = now

        cooldown = max(1.0, float(getattr(router.config, "safety_governor_cooldown_sec", 30.0)))
        last_action = float(getattr(router, "_safety_gov_last_action_ts", 0.0) or 0.0)

        snapshots = []
        try:
            if hasattr(router, "_build_snapshots"):
                snapshots = router._build_snapshots(regime=regime) or []
        except Exception:
            snapshots = []

        cycle_stats = {
            "accepted_trades": 1 if str(result.get("status", "")).upper() == "TRADE" else 0,
            "rejected_signals": self._is_rejection_result(result),
        }
        event = engine.monitor(
            router=router,
            context={
                "intelligence_report": dict(intelligence_report or {}),
                "snapshots": snapshots,
                "cycle_stats": cycle_stats,
                "feed_latency_ms": 0.0,
                "api_errors": 0,
            },
        )
        level = str(event.get("alert_level", "NONE")).upper()
        if level != "NONE":
            if last_action > 0.0 and (now - last_action) < cooldown:
                return {
                    "alert_level": level,
                    "reason": event.get("reason", ""),
                    "action": f"Suppressed by cooldown ({round(cooldown, 2)}s)",
                }
            router._safety_gov_last_action_ts = now
        return event

    def _is_rejection_result(self, result):
        status = str((result or {}).get("status", "")).upper()
        reason = str((result or {}).get("reason", "")).upper()
        if status == "TRADE":
            return 0
        # Only count true rejection/error-like outcomes as rejections.
        rejection_tokens = (
            "REJECT",
            "BROKER_ERROR",
            "ORDER_ERROR",
            "INVALID_SIGNAL",
            "FAILED",
        )
        return 1 if any(token in reason for token in rejection_tokens) else 0

    def _start_alpha_genome_engine(self, router):
        if not bool(getattr(router.config, "enable_alpha_genome_engine", False)):
            return None
        if not getattr(router, "alpha_genome_library", None) or not getattr(router, "alpha_genome_generator", None):
            return None
        interval = max(30.0, float(getattr(router.config, "alpha_genome_interval_sec", 300.0)))
        print(f"Alpha genome engine started: interval={interval}s")
        return self._track_task(asyncio.create_task(self._run_alpha_genome_loop(router, interval_sec=interval)), "alpha_genome")

    async def _run_alpha_genome_loop(self, router, interval_sec):
        lib = getattr(router, "alpha_genome_library", None)
        gen = getattr(router, "alpha_genome_generator", None)
        evalr = getattr(router, "alpha_genome_evaluator", None)
        if not lib or not gen:
            return
        shutdown = get_shutdown_handler()
        while self.runtime_state.is_running():
            if not self.runtime_state.is_running():
                break
            try:
                parents = lib.list(limit=40)
                if not parents:
                    genomes = gen.generate_random(count=max(1, int(getattr(router.config, "alpha_genome_random_count", 6))))
                else:
                    genomes = []
                    genomes.extend(gen.generate_from_mutation(parents, variants_per_base=max(1, int(getattr(router.config, "alpha_genome_mutation_variants", 2)))))
                    genomes.extend(gen.generate_from_crossbreeding(parents, children_count=max(1, int(getattr(router.config, "alpha_genome_cross_children", 4)))))
                for g in genomes:
                    lib.upsert_dict(g)

                reports = evalr.evaluate_genomes(genomes[:30]) if evalr else []
                top = sorted(reports, key=lambda r: float(r.get("fitness_score", 0.0)), reverse=True)[:3]
                if top:
                    self._emit_dashboard_event(
                        "ALPHA_GENOME_EVALUATION",
                        {"count": len(reports), "top": top},
                    )
                    if router.telegram:
                        router.telegram.send_message(
                            f"AlphaGenome: evaluated={len(reports)} top={top[0].get('genome_id')} fitness={round(float(top[0].get('fitness_score',0.0)),4)}"
                        )
                setattr(router, "alpha_genome_last_reports", reports)
            except Exception as exc:
                print(f"AlphaGenome error: {exc}")
            await asyncio.sleep(interval_sec)

    def _start_alpha_factory(self, router):
        controller = getattr(router, "alpha_factory_controller", None)
        if not controller:
            return None
        if not bool(getattr(router.config, "enable_alpha_factory", False)):
            return None
        poll = 30.0
        print("Alpha factory started.")
        return self._track_task(asyncio.create_task(self._run_alpha_factory_loop(router, poll_sec=poll)), "alpha_factory")

    async def _run_alpha_factory_loop(self, router, poll_sec):
        controller = getattr(router, "alpha_factory_controller", None)
        if not controller:
            return
        shutdown = get_shutdown_handler()
        while self.runtime_state.is_running():
            if not self.runtime_state.is_running():
                break
            try:
                report = controller.run_cycle()
                promotions = list(report.get("promoted_strategies", []) or [])
                if report.get("genomes_generated", 0) or report.get("candidates_filtered", 0) or promotions:
                    self._emit_dashboard_event("ALPHA_FACTORY_REPORT", report)
                if promotions and router.telegram:
                    router.telegram.send_message(
                        f"AlphaFactory: generated={report.get('genomes_generated',0)} filtered={report.get('candidates_filtered',0)} promoted={len(promotions)}"
                    )
                setattr(router, "alpha_factory_last_report", report)
            except Exception as exc:
                print(f"AlphaFactory error: {exc}")
            await asyncio.sleep(poll_sec)

    def _start_global_market_brain(self, router):
        engine = getattr(router, "global_market_brain", None)
        if not engine:
            return None
        if not bool(getattr(router.config, "enable_global_market_brain", False)):
            return None
        interval = max(10.0, float(getattr(router.config, "global_market_brain_interval_sec", 120.0)))
        print(f"Global Market Brain started: interval={interval}s")
        return self._track_task(asyncio.create_task(self._run_global_market_brain_loop(router, interval_sec=interval)), "global_market_brain")

    async def _run_global_market_brain_loop(self, router, interval_sec):
        engine = getattr(router, "global_market_brain", None)
        if not engine:
            return
        shutdown = get_shutdown_handler()
        while self.runtime_state.is_running():
            if not self.runtime_state.is_running():
                break
            try:
                snapshots = self._build_global_macro_snapshots(router)
                macro_inputs = self._build_macro_inputs(router)
                output = engine.analyze(snapshots=snapshots, macro_inputs=macro_inputs)
                engine.publish(
                    output=output,
                    market_pulse_engine=getattr(router, "market_pulse_engine", None),
                    meta_strategy_brain=getattr(router, "meta_strategy_brain", None),
                    portfolio_ai=getattr(router, "portfolio_ai_engine", None),
                    alpha_factory=getattr(router, "alpha_factory_controller", None),
                    adaptive_learning_engine=getattr(router, "adaptive_learning_engine", None),
                )
                setattr(router, "global_market_brain_last", output)

                if bool(getattr(router.config, "global_market_brain_dashboard_events", True)):
                    self._emit_dashboard_event("GLOBAL_MARKET_BRAIN", output)
                if bool(getattr(router.config, "global_market_brain_telegram_events", True)) and router.telegram:
                    router.telegram.send_message(
                        "GlobalMarketBrain: "
                        f"regime={output.get('regime')} "
                        f"vol={output.get('volatility_state')} "
                        f"liq={output.get('liquidity_state')} "
                        f"pref={output.get('preferred_strategy_type')}"
                    )
                print(
                    "GlobalMarketBrain: "
                    f"{output.get('regime')} | vol={output.get('volatility_state')} | "
                    f"liq={output.get('liquidity_state')} | pref={output.get('preferred_strategy_type')}"
                )
            except Exception as exc:
                print(f"GlobalMarketBrain error: {exc}")
            await asyncio.sleep(interval_sec)

    def _build_global_macro_snapshots(self, router):
        snapshots = []
        if hasattr(router, "_build_snapshots"):
            try:
                snapshots = list(router._build_snapshots(regime="MEAN_REVERSION") or [])
            except Exception:
                snapshots = []
        # enrich with return proxy for cross-asset analyzer
        out = []
        for row in snapshots:
            item = dict(row)
            closes = list(item.get("close", []) or [])
            if len(closes) >= 2 and float(closes[-2]) != 0.0:
                ret = (float(closes[-1]) - float(closes[-2])) / abs(float(closes[-2]))
            else:
                ret = 0.0
            item["return"] = ret
            out.append(item)
        return out

    def _build_macro_inputs(self, router):
        state = getattr(router, "state", None)
        dd = float(getattr(state, "total_drawdown_pct", 0.0) or 0.0) if state else 0.0
        realized = float(getattr(state, "realized_pnl", 0.0) or 0.0) if state else 0.0
        if realized > 0:
            growth_trend = 0.4
        elif realized < 0:
            growth_trend = -0.4
        else:
            growth_trend = 0.0
        inflation_trend = 0.3 if dd < 5.0 else 0.1
        vol_state = "NORMAL"
        if dd > 10.0:
            vol_state = "HIGH"
        return {
            "growth_trend": growth_trend,
            "inflation_trend": inflation_trend,
            "volatility_state": vol_state,
            "credit_spread_bps": 120.0 + (dd * 5.0),
            "policy_rate_pct": 6.0,
        }

    def _emit_dashboard_event(self, event_type, payload):
        try:
            from quant_ecosystem.operating.dashboard.system_state_api import SystemStateAPI

            SystemStateAPI.emit_global_event(event_type=event_type, payload=payload)
        except Exception:
            pass

    def _track_task(self, task, label):
        if task is None:
            return None
        setattr(task, "_qe_label", label)
        self._background_tasks.add(task)

        def _cleanup(done_task):
            self._background_tasks.discard(done_task)

        task.add_done_callback(_cleanup)
        return task

    async def _cancel_task(self, task, label):
        if task is None:
            return
        if task.done():
            self._background_tasks.discard(task)
            return
        logger.info("Cancelling task: %s", label)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            logger.info("Task cancelled cleanly: %s", label)
        except Exception as exc:
            logger.warning("Task cleanup error [%s]: %s", label, exc)
        finally:
            self._background_tasks.discard(task)

    async def _shutdown_service_task(self, router, task, server_attr, label):
        server = getattr(router, server_attr, None)
        if server is not None:
            logger.info("Stopping %s server...", label)
            if hasattr(server, "close"):
                try:
                    server.close()
                except Exception as exc:
                    logger.warning("%s server close() failed: %s", label, exc)
            if hasattr(server, "wait_closed"):
                try:
                    await server.wait_closed()
                except Exception as exc:
                    logger.warning("%s server wait_closed() failed: %s", label, exc)
            if hasattr(server, "should_exit"):
                server.should_exit = True
            if hasattr(server, "force_exit"):
                server.force_exit = True
        await self._cancel_task(task, label)
        setattr(router, server_attr, None)
        logger.info("%s server released.", label)

    async def _cancel_remaining_tasks(self):
        current = asyncio.current_task()
        tasks = [task for task in asyncio.all_tasks() if task is not current and not task.done()]
        if not tasks:
            return
        logger.info("Cancelling remaining active tasks: %s", [getattr(t, "_qe_label", repr(t)) for t in tasks])
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    def _prime_symbol_data(self, router):
        data_layer = getattr(router, "data_layer", None)
        state = getattr(router, "state", None)
        if not data_layer or state is None:
            return
        latest_prices = dict(getattr(state, "latest_prices", {}) or {})
        for symbol in list(getattr(router, "symbols", []) or [])[:10]:
            try:
                packet = data_layer.fetch_market_data(symbol=symbol, timeframe="5m", allow_synthetic=True)
                latest_prices[symbol] = float(packet.payload.get("latest_price", 0.0) or 0.0)
            except Exception as exc:
                logger.debug("[data_layer] symbol prime failed | symbol=%s error=%s", symbol, exc)
        state.latest_prices = latest_prices

    def _update_runtime_memory(self, router, cycle_id, intelligence_report, result):
        memory_engine = getattr(router, "memory_engine", None)
        if not memory_engine:
            return
        regime = intelligence_report.get("regime_advanced", intelligence_report.get("regime", result.get("regime", "UNKNOWN")))
        memory_engine.record_regime(
            regime,
            context={
                "cycle_id": cycle_id,
                "market_bias": intelligence_report.get("bias", "NEUTRAL"),
                "status": result.get("status", "UNKNOWN"),
            },
        )
        event_type = "NONE"
        thinking = dict(getattr(getattr(router, "state", None), "system_thinking", {}) or {})
        if thinking.get("event_type"):
            event_type = thinking.get("event_type")
        memory_engine.record_event(event_type, payload={"cycle_id": cycle_id, "status": result.get("status", "UNKNOWN")})
        strategy_id = str(result.get("strategy_id", "")).strip()
        if strategy_id:
            perf_log = self._load_json_file("storage/performance_log.json", default={})
            memory_engine.record_strategy_snapshot(strategy_id, perf_log.get(strategy_id, {}))

    def _load_json_file(self, path, default=None):
        import json

        try:
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception:
            return {} if default is None else default

    def _run_adaptive_learning(self, router, result, intelligence_report, cycle_id, batch_interval_cycles):
        engine = getattr(router, "adaptive_learning_engine", None)
        if not engine:
            return None
        if not bool(getattr(router.config, "enable_adaptive_learning", False)):
            return None
        try:
            trades = list(getattr(router.state, "trade_history", []) or [])
            if not hasattr(router, "_adaptive_last_trade_index"):
                router._adaptive_last_trade_index = 0
            defaults = {
                "regime": str(
                    result.get(
                        "regime",
                        intelligence_report.get("regime_advanced", intelligence_report.get("regime", "UNKNOWN")),
                    )
                ).upper(),
                "volatility": float(intelligence_report.get("volatility", 0.0) or 0.0),
            }

            if str(result.get("status")) == "TRADE" and trades:
                row = self._learning_payload_from_trade(
                    trade=trades[-1],
                    fallback_result=result,
                    defaults=defaults,
                )
                update = engine.ingest_trade_result(row, defaults=defaults)
                published = engine.publish_updates(
                    updates_payload=update,
                    strategy_lab=getattr(router, "strategy_lab_controller", None),
                    meta_strategy_brain=getattr(router, "meta_strategy_brain", None),
                    portfolio_ai=getattr(router, "portfolio_ai_engine", None),
                    execution_intelligence=getattr(router, "execution_brain", None),
                )
                router._adaptive_last_trade_index = len(trades)
                return {
                    "mode": "trade",
                    "updates": len(update.get("updates", [])),
                    "published": int(published.get("published", 0)),
                }

            if (int(cycle_id) % max(1, int(batch_interval_cycles))) != 0:
                return None
            start_idx = int(getattr(router, "_adaptive_last_trade_index", 0) or 0)
            if len(trades) <= start_idx:
                return None
            new_trades = trades[start_idx:]
            batch_rows = [
                self._learning_payload_from_trade(trade=row, fallback_result=result, defaults=defaults)
                for row in new_trades
            ]
            update = engine.ingest_trade_batch(batch_rows, defaults=defaults)
            published = engine.publish_updates(
                updates_payload=update,
                strategy_lab=getattr(router, "strategy_lab_controller", None),
                meta_strategy_brain=getattr(router, "meta_strategy_brain", None),
                portfolio_ai=getattr(router, "portfolio_ai_engine", None),
                execution_intelligence=getattr(router, "execution_brain", None),
            )
            router._adaptive_last_trade_index = len(trades)
            return {
                "mode": "batch",
                "rows": len(batch_rows),
                "updates": len(update.get("updates", [])),
                "published": int(published.get("published", 0)),
            }
        except Exception as exc:
            return {"error": str(exc)}

    def _learning_payload_from_trade(self, trade, fallback_result, defaults):
        trade = dict(trade or {})
        fallback = dict(fallback_result or {})
        symbol = str(trade.get("symbol", fallback.get("symbol", ""))).strip()
        side = str(trade.get("side", fallback.get("side", "BUY"))).upper()
        price = float(trade.get("price", fallback.get("price", 0.0)) or 0.0)
        qty = float(trade.get("qty", fallback.get("qty", 0.0)) or 0.0)
        realized = float(trade.get("realized_pnl", 0.0) or 0.0)
        cycle_pnl = float(trade.get("cycle_pnl", fallback.get("pnl", 0.0)) or 0.0)
        pnl = realized if abs(realized) > 1e-12 else cycle_pnl
        timestamp = str(
            trade.get("timestamp")
            or datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        )
        return {
            "symbol": symbol,
            "strategy_id": str(trade.get("strategy_id", fallback.get("strategy_id", ""))).strip(),
            "entry_price": price,
            "exit_price": price,
            "pnl": pnl,
            "execution_slippage": float(trade.get("slippage_bps", 0.0) or 0.0),
            "regime": str(trade.get("regime", defaults.get("regime", "UNKNOWN"))).upper(),
            "volatility": float(defaults.get("volatility", 0.0) or 0.0),
            "timestamp": timestamp,
            "side": side,
            "qty": qty,
        }

    def _run_cognitive_controller(self, router, regime_advanced):
        controller = getattr(router, "cognitive_controller", None)
        if not controller:
            return None
        if not bool(getattr(router.config, "enable_cognitive_control", False)):
            return None
        try:
            interval_sec = max(0.5, float(getattr(router.config, "cognitive_control_interval_sec", 2.0)))
            outcome = controller.run_if_due(
                router=router,
                regime=str(regime_advanced).upper(),
                interval_sec=interval_sec,
            )
            if not outcome:
                return None
            decision = dict(outcome.get("decision", {}))
            return {
                "mode": decision.get("system_mode", "BALANCED"),
                "risk": decision.get("portfolio_risk_level", "MEDIUM"),
                "pref": decision.get("preferred_strategy_type", "MIXED"),
                "actions": decision.get("actions", []),
                "latency_ms": round(float(outcome.get("latency_ms", 0.0)), 3),
            }
        except Exception as exc:
            return {"error": str(exc)}

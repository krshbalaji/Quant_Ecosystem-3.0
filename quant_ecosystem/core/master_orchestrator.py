import asyncio
from datetime import datetime
import time

from quant_ecosystem.control.telegram_control_center import TelegramControlCenter
from quant_ecosystem.core.health.health_check import HealthCheck
from quant_ecosystem.core.persistence.runtime_store import RuntimeStore
from quant_ecosystem.core.scheduler import Scheduler
from quant_ecosystem.core.strategy_lifecycle_manager import StrategyLifecycleManager
from quant_ecosystem.core.strategy_portfolio_manager import StrategyPortfolioManager
from quant_ecosystem.intelligence.adaptation_engine import AdaptationEngine
from quant_ecosystem.intelligence.global_intelligence_engine import GlobalIntelligenceEngine
from quant_ecosystem.market.market_universe_manager import MarketUniverseManager
from quant_ecosystem.reporting.eod.eod_report import EODReport
from quant_ecosystem.risk.black_swan_guard import BlackSwanGuard
from quant_ecosystem.risk.safety_layer import SafetyLayer
from quant_ecosystem.risk.survival_playbook import SurvivalPlaybook
from quant_ecosystem.strategy_bank.strategy_evaluator import StrategyEvaluator


class MasterOrchestrator:

    def __init__(self, system_or_router):
        # Support both direct System container or ExecutionRouter with a
        # .system attribute, while always exposing engines via self.system.
        self.system = getattr(system_or_router, "system", system_or_router)
        self.router_ref = getattr(system_or_router, "execution_router", None)
        self.cycles = 30
        self.scheduler = Scheduler()
        self.health_check = HealthCheck()
        self.adaptation_engine = AdaptationEngine()
        self.intelligence_engine = GlobalIntelligenceEngine()
        self.strategy_evaluator = StrategyEvaluator()
        self.strategy_portfolio = StrategyPortfolioManager()
        self.strategy_lifecycle = StrategyLifecycleManager()
        self.universe = MarketUniverseManager()
        self.reporter = EODReport()
        self.runtime_store = RuntimeStore()
        self.safety = SafetyLayer()
        self.black_swan = BlackSwanGuard()
        self.survival = SurvivalPlaybook()
        self.control_center = TelegramControlCenter()

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
        print("Quant Ecosystem 3.0 booting...")
        self.scheduler.start_day()

        if hasattr(self.system, "market_data"):
            asyncio.create_task(self.system.market_data.start())

        if hasattr(self.system, "alpha_competition") and self.system.alpha_competition:
            # Research engine: strategy Darwinism
            if hasattr(self.system.alpha_competition, "evaluate"):
                self.system.alpha_competition.evaluate()
            elif hasattr(self.system.alpha_competition, "run"):
                self.system.alpha_competition.run()

        if hasattr(self.system, "strategy_discovery"):

            if self.system.strategy_discovery:
                self.system.strategy_discovery.discover()
            else:
                logger.warning("StrategyDiscoveryEngine not available — skipping discovery.")
            
        if hasattr(self.system, "capital_intelligence") and self.system.capital_intelligence:
            # Capital allocation intelligence layer
            if hasattr(self.system.capital_intelligence, "evaluate"):
                self.system.capital_intelligence.evaluate()
            elif hasattr(self.system.capital_intelligence, "run"):
                self.system.capital_intelligence.run()

        if hasattr(self.system, "alpha_evolution") and self.system.alpha_evolution:
            # Evolutionary engine for strategies
            if hasattr(self.system.alpha_evolution, "evolve"):
                self.system.alpha_evolution.evolve()
            elif hasattr(self.system.alpha_evolution, "run"):
                self.system.alpha_evolution.run()

        health = self.health_check.run(router=router)
        if not health.get("broker_connected", False):
            print("Health check failed: broker not connected. Aborting session.")
            return

        if router.telegram:
            sent = router.telegram.send_startup_ping()
            if sent:
                print("Telegram startup alert sent.")
            else:
                print("Telegram startup alert not sent (check token/chat id).")

        if router.strategy_engine:
            router.strategy_engine.reload()
            strategy_reports = self.strategy_evaluator.evaluate(router.strategy_engine.strategies)
            strategy_reports = self._apply_lifecycle(strategy_reports)

            bank_engine = getattr(router, "strategy_bank_engine", None)
            if bank_engine and getattr(bank_engine, "enabled", False):
                strategy_reports = bank_engine.ingest_reports(strategy_reports)

            portfolio_plan = self.strategy_portfolio.build_portfolio(strategy_reports)
            strategy_reports = portfolio_plan["reports"]
            router.strategy_engine.apply_policy(strategy_reports)
            top = strategy_reports[:3]
            print(f"Strategy evaluation top-3: {top}")
            print(f"Active strategy ids: {list(getattr(router.strategy_engine, 'active_ids', []) or [])}")
            if bank_engine and getattr(bank_engine, "enabled", False):
                allocation_snapshot = {
                    sid: bank_engine.get_allocation(sid)
                    for sid in bank_engine.get_active_strategies()
                }
                print(f"Strategy bank allocations: {allocation_snapshot}")
        else:
            strategy_reports = []

        intelligence_report = self.intelligence_engine.analyze()
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

        if getattr(router.config, "enable_global_session_fallback", True):
            classes = self.universe.asset_classes_for_session()
        else:
            classes = ["stocks", "indices"]
        router.symbols = self.universe.symbols(asset_classes=classes, regime=regime_advanced, limit=8)
        router.execution_lock = getattr(router, "execution_lock", asyncio.Lock())
        command_task = asyncio.create_task(self._poll_telegram_commands(router))
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
            # New alpha idea generation
            if hasattr(self.system.alpha_discovery, "discover"):
                self.system.alpha_discovery.discover()
            elif hasattr(self.system.alpha_discovery, "run"):
                self.system.alpha_discovery.run()

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
            for i in range(1, self.cycles + 1):
                print(f"Cycle {i}")
                refresh_every = max(1, int(getattr(router.config, "intelligence_refresh_cycles", 5)))
                if i > 1 and (i % refresh_every == 0):
                    intelligence_report = self.intelligence_engine.analyze()
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

                if getattr(router.config, "enable_global_session_fallback", True):
                    classes = self.universe.asset_classes_for_session()
                else:
                    classes = ["stocks", "indices"]
                router.symbols = self.universe.symbols(asset_classes=classes, regime=regime_advanced, limit=8)

                # Institutional loop hook
                self._run_institutional_cycle(
                    router=router,
                    cycle_id=i,
                    regime=regime,
                    market_bias=market_bias,
                    intelligence_report=intelligence_report,
                )
                async with router.execution_lock:
                    result = await router.execute(market_bias=market_bias, regime=regime)

                if result["status"] == "TRADE":
                    print(
                        "Executed |",
                        result["strategy_id"],
                        result["symbol"],
                        result["side"],
                        "qty",
                        result["qty"],
                        "PnL",
                        result["pnl"],
                    )
                else:
                    print("Skipped | Reason:", result["reason"])

                self.runtime_store.write_cycle(
                    cycle_id=i,
                    result=result,
                    state=router.state,
                )
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
            command_task.cancel()
            with_cancel = command_task
            try:
                await with_cancel
            except asyncio.CancelledError:
                pass
            if alpha_task:
                alpha_task.cancel()
                try:
                    await alpha_task
                except asyncio.CancelledError:
                    pass
            if portfolio_ai_task:
                portfolio_ai_task.cancel()
                try:
                    await portfolio_ai_task
                except asyncio.CancelledError:
                    pass
            if strategy_lab_task:
                strategy_lab_task.cancel()
                try:
                    await strategy_lab_task
                except asyncio.CancelledError:
                    pass
            if event_signal_task:
                event_signal_task.cancel()
                try:
                    await event_signal_task
                except asyncio.CancelledError:
                    pass
            if market_pulse_task:
                market_pulse_task.cancel()
                try:
                    await market_pulse_task
                except asyncio.CancelledError:
                    pass
            if event_orchestrator_task:
                event_orchestrator_task.cancel()
                try:
                    await event_orchestrator_task
                except asyncio.CancelledError:
                    pass
            if dashboard_task:
                try:
                    srv = getattr(router, "_dashboard_uvicorn_server", None)
                    if srv is not None:
                        srv.should_exit = True
                    await asyncio.wait_for(dashboard_task, timeout=5.0)
                except asyncio.TimeoutError:
                    dashboard_task.cancel()
                    try:
                        await dashboard_task
                    except asyncio.CancelledError:
                        pass
                except asyncio.CancelledError:
                    pass
            if cockpit_task:
                try:
                    srv = getattr(router, "_cockpit_uvicorn_server", None)
                    if srv is not None:
                        srv.should_exit = True
                    await asyncio.wait_for(cockpit_task, timeout=5.0)
                except asyncio.TimeoutError:
                    cockpit_task.cancel()
                    try:
                        await cockpit_task
                    except asyncio.CancelledError:
                        pass
                except asyncio.CancelledError:
                    pass
            if shadow_task:
                shadow_task.cancel()
                try:
                    await shadow_task
                except asyncio.CancelledError:
                    pass
            if alpha_genome_task:
                alpha_genome_task.cancel()
                try:
                    await alpha_genome_task
                except asyncio.CancelledError:
                    pass
            if alpha_factory_task:
                alpha_factory_task.cancel()
                try:
                    await alpha_factory_task
                except asyncio.CancelledError:
                    pass
            if global_brain_task:
                global_brain_task.cancel()
                try:
                    await global_brain_task
                except asyncio.CancelledError:
                    pass

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
        if git_sync and auto_push_end:
            git_sync.push_on_end(create_eod_tag=auto_tag_end)
        print("Session complete")

    async def _poll_telegram_commands(self, router):
        if not router.telegram:
            return

        while True:
            commands = router.telegram.consume_webhook_events()
            for command, result in commands:
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
                    selector.activation_manager.apply_selection(
                        selected_ids=allowed_ids,
                        available_ids=available_ids,
                    )
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
            selector = getattr(router, "strategy_selector", None)
            layer = getattr(router, "strategy_bank_layer", None)
            if selector and hasattr(selector, "activation_manager") and layer and hasattr(layer, "registry_rows"):
                try:
                    rows = layer.registry_rows()
                    active_ids = [
                        str(row.get("id"))
                        for row in rows
                        if row.get("id") and bool(row.get("active", False))
                    ]
                    available_ids = [str(row.get("id")) for row in rows if row.get("id")]
                    selector.activation_manager.apply_selection(
                        selected_ids=active_ids,
                        available_ids=available_ids,
                    )
                except Exception:
                    pass
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
        return asyncio.create_task(scanner.run_forever(top_n=top_n))

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
        return asyncio.create_task(self._run_portfolio_ai_loop(router, interval, capital_pct))

    async def _run_portfolio_ai_loop(self, router, interval_sec, capital_pct):
        engine = getattr(router, "portfolio_ai_engine", None)
        if not engine:
            return
        while True:
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
        return asyncio.create_task(
            self._run_strategy_lab_loop(
                router=router,
                interval_sec=interval,
                generate_count=generate_count,
                variants_per_base=variants_per_base,
                periods=periods,
            )
        )

    async def _run_strategy_lab_loop(self, router, interval_sec, generate_count, variants_per_base, periods):
        controller = getattr(router, "strategy_lab_controller", None)
        if not controller:
            return
        while True:
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
        return asyncio.create_task(self._run_event_signal_loop(router, poll_sec=poll_sec))

    async def _run_event_signal_loop(self, router, poll_sec):
        engine = getattr(router, "event_signal_engine", None)
        if not engine:
            return
        while True:
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
        return asyncio.create_task(self._run_market_pulse_loop(router, poll_sec=poll_sec))

    async def _run_market_pulse_loop(self, router, poll_sec):
        engine = getattr(router, "market_pulse_engine", None)
        if not engine:
            return
        while True:
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
        return asyncio.create_task(orchestrator.run_forever())

    def _start_dashboard_service(self, router):
        cfg = getattr(router, "dashboard_service_config", {}) or {}
        if not bool(cfg.get("enabled", False)):
            return None
        host = str(cfg.get("host", "127.0.0.1"))
        port = int(cfg.get("port", 8090))
        interval = max(0.1, float(cfg.get("update_interval_sec", 0.25)))
        print(f"Dashboard service starting: http://{host}:{port} interval={interval}s")
        return asyncio.create_task(
            self._run_dashboard_service(router=router, host=host, port=port, interval=interval)
        )

    async def _run_dashboard_service(self, router, host, port, interval):
        try:
            from quant_ecosystem.dashboard.dashboard_server import create_dashboard_app
            import uvicorn
        except Exception as exc:
            print(f"Dashboard service unavailable: {exc}")
            return
        app = create_dashboard_app(
            router_provider=lambda: router,
            update_interval_sec=interval,
        )
        server = uvicorn.Server(uvicorn.Config(app=app, host=host, port=int(port), log_level="warning"))
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
        return asyncio.create_task(
            self._run_cockpit_service(
                router=router,
                host=host,
                port=port,
                interval=interval,
                auth_token=str(cfg.get("auth_token", "")),
            )
        )

    async def _run_cockpit_service(self, router, host, port, interval, auth_token):
        try:
            from quant_ecosystem.cockpit.cockpit_server import create_cockpit_app
            import uvicorn
        except Exception as exc:
            print(f"Cockpit service unavailable: {exc}")
            return
        app = create_cockpit_app(
            router_provider=lambda: router,
            update_interval_sec=interval,
            auth_token=auth_token,
        )
        server = uvicorn.Server(uvicorn.Config(app=app, host=host, port=int(port), log_level="warning"))
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
        return asyncio.create_task(self._run_shadow_trading_loop(router, interval_sec=interval))

    async def _run_shadow_trading_loop(self, router, interval_sec):
        engine = getattr(router, "shadow_trading_engine", None)
        if not engine:
            return
        while True:
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
        return asyncio.create_task(self._run_alpha_genome_loop(router, interval_sec=interval))

    async def _run_alpha_genome_loop(self, router, interval_sec):
        lib = getattr(router, "alpha_genome_library", None)
        gen = getattr(router, "alpha_genome_generator", None)
        evalr = getattr(router, "alpha_genome_evaluator", None)
        if not lib or not gen:
            return
        while True:
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
        return asyncio.create_task(self._run_alpha_factory_loop(router, poll_sec=poll))

    async def _run_alpha_factory_loop(self, router, poll_sec):
        controller = getattr(router, "alpha_factory_controller", None)
        if not controller:
            return
        while True:
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
        return asyncio.create_task(self._run_global_market_brain_loop(router, interval_sec=interval))

    async def _run_global_market_brain_loop(self, router, interval_sec):
        engine = getattr(router, "global_market_brain", None)
        if not engine:
            return
        while True:
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
            from quant_ecosystem.dashboard.system_state_api import SystemStateAPI

            SystemStateAPI.emit_global_event(event_type=event_type, payload=payload)
        except Exception:
            pass

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

router.research_memory.create_snapshot("session_end")
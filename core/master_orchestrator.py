import asyncio

from control.telegram_control_center import TelegramControlCenter
from core.health.health_check import HealthCheck
from core.persistence.runtime_store import RuntimeStore
from core.scheduler import Scheduler
from core.strategy_lifecycle_manager import StrategyLifecycleManager
from core.strategy_portfolio_manager import StrategyPortfolioManager
from intelligence.adaptation_engine import AdaptationEngine
from intelligence.global_intelligence_engine import GlobalIntelligenceEngine
from market.market_universe_manager import MarketUniverseManager
from reporting.eod.eod_report import EODReport
from risk.black_swan_guard import BlackSwanGuard
from risk.safety_layer import SafetyLayer
from risk.survival_playbook import SurvivalPlaybook
from strategy_bank.strategy_evaluator import StrategyEvaluator


class MasterOrchestrator:

    def __init__(self):
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

    async def start(self, router, git_sync=None, auto_push_end=True, auto_tag_end=True):
        print("Quant Ecosystem 3.0 booting...")
        self.scheduler.start_day()

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

        if getattr(router.config, "enable_global_session_fallback", True):
            classes = self.universe.asset_classes_for_session()
        else:
            classes = ["stocks", "indices"]
        router.symbols = self.universe.symbols(asset_classes=classes, regime=regime_advanced, limit=8)
        command_task = asyncio.create_task(self._poll_telegram_commands(router))

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

                if getattr(router.config, "enable_global_session_fallback", True):
                    classes = self.universe.asset_classes_for_session()
                else:
                    classes = ["stocks", "indices"]
                router.symbols = self.universe.symbols(asset_classes=classes, regime=regime_advanced, limit=8)
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

        adaptation_report = self.adaptation_engine.apply(router.state, router.risk_engine)
        print(f"Adaptation: {adaptation_report}")

        if getattr(router, "outcome_memory", None):
            router.outcome_memory.update_from_trades(router.state.trade_history)

        mutation_engine = getattr(router, "mutation_engine", None)
        if mutation_engine and getattr(mutation_engine, "enabled", False):
            mutated = mutation_engine.run_daily(strategy_reports)
            if mutated:
                print(f"Mutation engine accepted candidates: {len(mutated)}")

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
        detector = getattr(router, "market_regime_detector", None)
        if not detector:
            return None
        timeframe_data = self._build_regime_timeframe_data(router)
        if not timeframe_data:
            return None
        extra = {
            "market_breadth": intelligence_report.get("market_breadth", 0.0),
            "vix": intelligence_report.get("vix"),
        }
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
                "alloc": allocation.get("allocation", {}),
                "rebalanced": allocation.get("rebalanced", False),
            }
        except Exception as exc:
            return {"regime": str(regime_advanced).upper(), "error": str(exc)}

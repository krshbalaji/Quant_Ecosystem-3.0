import asyncio

from core.health.health_check import HealthCheck
from core.persistence.runtime_store import RuntimeStore
from core.scheduler import Scheduler
from intelligence.adaptation_engine import AdaptationEngine
from intelligence.global_intelligence_engine import GlobalIntelligenceEngine
from reporting.eod.eod_report import EODReport
from risk.safety_layer import SafetyLayer
from strategy_bank.strategy_evaluator import StrategyEvaluator


class MasterOrchestrator:

    def __init__(self):
        self.cycles = 30
        self.scheduler = Scheduler()
        self.health_check = HealthCheck()
        self.adaptation_engine = AdaptationEngine()
        self.intelligence_engine = GlobalIntelligenceEngine()
        self.strategy_evaluator = StrategyEvaluator()
        self.reporter = EODReport()
        self.runtime_store = RuntimeStore()
        self.safety = SafetyLayer()

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
            router.strategy_engine.apply_policy(strategy_reports)
            top = strategy_reports[:3]
            print(f"Strategy evaluation top-3: {top}")
        else:
            strategy_reports = []

        intelligence_report = self.intelligence_engine.analyze()
        market_bias = intelligence_report.get("bias", "NEUTRAL")
        regime = intelligence_report.get("regime", "MEAN_REVERSION")
        command_task = asyncio.create_task(self._poll_telegram_commands(router))

        try:
            for i in range(1, self.cycles + 1):
                print(f"Cycle {i}")
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

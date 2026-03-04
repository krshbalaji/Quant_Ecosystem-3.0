import os
from pathlib import Path

PROJECT_NAME = "quant_ecosystem"

folders = [

# CORE SYSTEM
"core",
"core/health",
"core/scheduler",
"core/capital",
"core/state",

# BROKER LAYER
"broker",
"broker/adapters",

# EXECUTION
"execution",
"execution/risk",
"execution/orders",

# STRATEGY BANK
"strategy_bank",
"strategy_bank/raw",
"strategy_bank/validated",
"strategy_bank/paper",
"strategy_bank/live",

# INTELLIGENCE
"intelligence",
"intelligence/market",
"intelligence/news",
"intelligence/regime",
"intelligence/volatility",
"intelligence/patterns",

# RESEARCH
"research",
"research/backtest",
"research/montecarlo",
"research/walkforward",
"research/optimizer",

# REPORTING
"reporting",
"reporting/eod",
"reporting/analytics",
"reporting/export",

# TELEGRAM CONTROL
"control",
"control/telegram",
"control/security",

# MANUAL TRADING DESK
"manual_desk",

# DATA
"data",
"data/market",
"data/logs",
"data/reports",
"data/equity",

# CONFIG
"config",

# UTILS
"utils"

]

files = {

# launcher
"launcher.py":"""
from quant_ecosystem.core.orchestrator import Orchestrator

if __name__ == "__main__":
    orchestrator = Orchestrator()
    orchestrator.start()
""",

# orchestrator
"core/orchestrator.py":"""
from quant_ecosystem.core.scheduler import Scheduler
from quant_ecosystem.core.health.health_check import HealthCheck

class Orchestrator:

    def __init__(self):

        self.scheduler = Scheduler()
        self.health = HealthCheck()

    def start(self):

        print("🚀 Quant Ecosystem Starting")

        self.health.run()

        self.scheduler.start_day()
""",

# scheduler
"core/scheduler.py":"""
import datetime

class Scheduler:

    def start_day(self):

        now = datetime.datetime.now()

        print("📅 Scheduler Active:", now)

        print("7:30 → Health Check")
        print("8:00 → Global Market Analysis")
        print("9:15 → Market Execution Mode")
""",

# health check
"core/health/health_check.py":"""
class HealthCheck:

    def run(self):

        print("🔎 Running system diagnostics...")
""",

# broker manager
"broker/broker_manager.py":"""
class BrokerManager:

    def connect(self):

        print("Connecting broker...")
""",

# fyers adapter
"broker/adapters/fyers_adapter.py":"""
class FyersAdapter:

    def login(self):

        print("Fyers broker connected")
""",

# execution router
"execution/execution_router.py":"""
class ExecutionRouter:

    def route(self):

        print("Routing trade execution")
""",

# capital allocator
"core/capital/capital_allocator.py":"""
class CapitalAllocator:

    def allocate(self):

        print("Allocating capital across strategies")
""",

# strategy registry
"strategy_bank/strategy_registry.py":"""
class StrategyRegistry:

    def load_strategies(self):

        print("Loading strategies")
""",

# backtest engine
"research/backtest/backtest_engine.py":"""
class BacktestEngine:

    def run(self):

        print("Running institutional backtest")
""",

# reporting
"reporting/eod/eod_report.py":"""
class EODReport:

    def generate(self):

        print("Generating EOD report")
""",

# telegram controller
"control/telegram/telegram_controller.py":"""
class TelegramController:

    def start(self):

        print("Telegram control active")
""",

# system state
"core/state/system_state.py":"""
class SystemState:

    def __init__(self):

        self.equity = 100000
        self.drawdown = 0
        self.trades_today = 0
"""
}


def build_project():

    root = Path(PROJECT_NAME)

    for folder in folders:
        path = root / folder
        os.makedirs(path, exist_ok=True)

    for file, content in files.items():
        path = root / file
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    print("✅ Quant Ecosystem structure created")


if __name__ == "__main__":
    build_project()
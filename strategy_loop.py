import time

from infra.execution_router import route_execution
from infra.logger import get_logger
from indicator_adapter import IndicatorAdapter
from strategy_brain import StrategyBrain

logger = get_logger(__name__)

indicators = IndicatorAdapter()
brain = StrategyBrain(indicators)

from portfolio_allocator_v2 import PortfolioAllocatorV2

allocator = PortfolioAllocatorV2(capital=100000)

signals = [
    {"symbol": "TCS.NS", "strength": 0.7},
    {"symbol": "RELIANCE.NS", "strength": 0.7}
]

market_data = {
    "TCS.NS": {"price": 3800, "atr": 40},
    "RELIANCE.NS": {"price": 2900, "atr": 35}
}

allocations = allocator.allocate(signals, market_data)

for trade in allocations:
    route_execution(trade)

SCAN_INTERVAL = 30

last_signal_time = {}
COOLDOWN = 30


def send_signal(signal):
    payload = {
        "symbol": signal["symbol"],
        "side": signal["side"],
        "qty": 1,
        "strength": signal["strength"],
    }

    response = route_execution(payload)
    if response.get("success"):
        if response.get("mode") == "local":
            logger.info("📡 Signal routed to local mode: %s", payload)
        else:
            logger.info("📡 SIGNAL SENT: %s", payload)
    else:
        logger.error("❌ Signal rejected: %s", response.get("error"))


logger.info("🧠 Multi-Strategy Brain Started...")

while True:
    from config import Config

    for symbol in Config.TRADE_SYMBOLS:

        sig = brain.decide(symbol)

        if not sig:
            continue

        now = time.time()

        if symbol in last_signal_time:
            if now - last_signal_time[symbol] < COOLDOWN:
                continue

        last_signal_time[symbol] = now

        print("📊 Decision:", sig)
        send_signal(sig)

    time.sleep(SCAN_INTERVAL)
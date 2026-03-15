import logging
import time
import os

from quant_ecosystem.core.system_factory import SystemFactory
from quant_ecosystem.core.market_mode import MarketModeController, MarketMode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():

    mode = os.getenv("TRADING_MODE", "PAPER")

    logger.info(f"[main] Quant Ecosystem 3.0 booting — mode={mode}")

    config = {
        "mode": mode,
        "telegram_token": os.getenv("TELEGRAM_BOT_TOKEN"),
        "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID"),
    }

    factory = SystemFactory()
    
    factory._config.autonomous_promote_threshold = -0.50

    router = factory.build()

    MarketModeController.set_mode(MarketMode.SYNTH)
    
    # START EXECUTION LOOP
    if hasattr(router, "execution_router"):

        er = router.execution_router

        if hasattr(er, "start"):
            er.start()

        elif hasattr(er, "run_forever"):
            er.run_forever()

        elif hasattr(er, "run"):
            er.run()

    logger.info("Boot completed.")

    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutdown requested")
            break


if __name__ == "__main__":
    main()
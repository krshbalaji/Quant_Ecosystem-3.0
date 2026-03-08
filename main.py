import logging
import time
import os

from quant_ecosystem.core.system_factory import SystemFactory

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

    factory = SystemFactory(config)

    router = factory.build()

    logger.info("Boot completed.")

    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutdown requested")
            break


if __name__ == "__main__":
    main()
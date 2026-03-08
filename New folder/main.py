import logging
import time

from quant_ecosystem.core.system_factory import SystemFactory

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger("main")


class Config:

    mode = "PAPER"

    telegram_token = ""
    telegram_chat_id = ""


def main():

    config = Config()

    logger.info(f"[main] Quant Ecosystem 3.0 booting — mode={config.mode}")

    factory = SystemFactory(config)

    router = factory.build()

    logger.info("Boot completed.")

    # telegram polling loop

    while True:

        try:

            if hasattr(router, "telegram") and router.telegram:
                router.telegram.consume_webhook_events()

        except Exception as e:
            logger.warning(f"Telegram loop error: {e}")

        time.sleep(1)


if __name__ == "__main__":
    main()
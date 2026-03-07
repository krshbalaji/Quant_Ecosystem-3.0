"""
Quant Ecosystem 3.0 — Main Boot Entry
Institutional Boot Loader
"""

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s"
)

logger = logging.getLogger("main")


class Config:
    """
    Minimal runtime config container.
    Later this will load from .env / config.yaml.
    """
    def __init__(self):

        self.mode = "PAPER"
        self.symbols = ["NSE:SBIN-EQ", "NSE:RELIANCE-EQ", "NSE:TCS-EQ"]

        # risk defaults
        self.max_daily_loss_pct = 5

        # telegram
        self.telegram_token = None
        self.telegram_chat_id = None


def main():

    config = Config()

    print(f"[main] Quant Ecosystem 3.0 booting — mode={config.mode}")

    try:

        from quant_ecosystem.core.system_factory import SystemFactory

        factory = SystemFactory(config)

        router = factory.build()

    except Exception as e:

        logger.exception("System boot failed")
        sys.exit(1)

    # Telegram boot notification
    try:

        if router.telegram:
            router.telegram.send("🚀 Quant Ecosystem boot completed")

    except Exception:
        pass

    print("Boot completed.")


if __name__ == "__main__":
    main()
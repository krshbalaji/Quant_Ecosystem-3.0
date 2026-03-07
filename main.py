import logging
import sys
from dotenv import load_dotenv
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s"
)

logger = logging.getLogger("main")


class Config:

    def __init__(self):

        load_dotenv()

        self.mode = "PAPER"
        self.symbols = ["NSE:SBIN-EQ", "NSE:RELIANCE-EQ", "NSE:TCS-EQ"]

        self.max_daily_loss_pct = 5

        self.telegram_token = os.getenv("TELEGRAM_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

    def get(self, key, default=None):
        return getattr(self, key, default)
    
    
def main():

    config = Config()

    print(f"[main] Quant Ecosystem 3.0 booting — mode={config.mode}")

    try:

        from quant_ecosystem.core.system_factory import SystemFactory

        factory = SystemFactory(config)

        router = factory.build()

    except Exception:

        logger.exception("System boot failed")
        sys.exit(1)


    # Telegram boot notification
    try:

        if router.telegram:
            router.telegram.send_message("🚀 Quant Ecosystem boot completed")
            router.telegram.send_message("Quant Ecosystem boot test message")

    except Exception:
        pass


    print("Boot completed.")

    if hasattr(router, "strategy_discovery_engine"):
        import threading

        threading.Thread(
            target=router.strategy_discovery_engine.start,
            daemon=True
        ).start()
        
    # start telegram command loop
    import time

    if router.telegram:
        while True:
            router.telegram.consume_webhook_events()
            time.sleep(1)

if __name__ == "__main__":
    main()
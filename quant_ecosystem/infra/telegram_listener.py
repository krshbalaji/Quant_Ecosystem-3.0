import requests
import time
import logging
from quant_ecosystem.config.telegram_config import TELEGRAM_BOT_TOKEN

logger = logging.getLogger(__name__)

URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def listen_for_commands(handler):

    offset = None

    while True:

        params = {"timeout": 100}

        if offset:
            params["offset"] = offset

        r = requests.get(f"{URL}/getUpdates", params=params).json()

        if not r.get("ok"):
            time.sleep(5)
            continue

        updates = r.get("result", [])

        for result in updates:

            offset = result["update_id"] + 1

            if "message" not in result:
                continue

            text = result["message"]["text"]

            handler(text)

        time.sleep(1)
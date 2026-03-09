import requests
import logging
from quant_ecosystem.config.telegram_config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    telegram_enabled
)

logger = logging.getLogger(__name__)

TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"


def send_message(text):

    if not telegram_enabled():
        logger.warning("Telegram disabled — credentials missing")
        return

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }

    try:
        requests.post(TELEGRAM_URL, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")
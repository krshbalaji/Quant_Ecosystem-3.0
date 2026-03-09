import os

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def telegram_enabled():
    return TELEGRAM_BOT_TOKEN is not None and TELEGRAM_CHAT_ID is not None
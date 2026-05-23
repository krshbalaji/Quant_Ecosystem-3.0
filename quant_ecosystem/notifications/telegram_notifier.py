import os
import requests


class TelegramNotifier:
    def __init__(self):
        self.bot_token = (os.getenv("TELEGRAM_BOT_TOKEN", "") or "").strip()
        self.chat_id = (os.getenv("TELEGRAM_CHAT_ID", "") or "").strip()

    def enabled(self):
        return bool(self.bot_token and self.chat_id)

    def send(self, message: str):
        if not self.enabled():
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown",
        }

        try:
            r = requests.post(url, json=payload, timeout=10)
            return r.status_code == 200
        except Exception:
            return False
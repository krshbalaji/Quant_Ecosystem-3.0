"""
PATCH: quant_ecosystem/telegram/telegram_control_center.py
FIX:   - Constructor now accepts config=None (was no-arg, caused TypeError
         when SystemFactory called TelegramControlCenter(config=...)).
       - Added send() method: falls back to print() when no token is
         configured; uses requests for real Telegram delivery when
         TELEGRAM_TOKEN and TELEGRAM_CHAT_ID are present in config.
"""
import os
import requests
from dotenv import load_dotenv


class TelegramControlCenter:

    def __init__(self, config=None):

        load_dotenv()

        self.token = os.getenv("TELEGRAM_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")

        if config:
            self.token = config.get("TELEGRAM_TOKEN", self.token)
            self.chat_id = config.get("TELEGRAM_CHAT_ID", self.chat_id)
            
        if not self.token or not self.chat_id:
            print("Telegram disabled: missing token or chat id")
            self.enabled = False
        else:
            self.enabled = True
            
    def send(self, message):

        if not self.enabled:
            print("[TELEGRAM DISABLED]", message)
            return

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"

        payload = {
            "chat_id": self.chat_id,
            "text": message
        }
        
        print("Telegram URL:", url)
        
        try:
            r = requests.post(url, json=payload, timeout=10)

            if r.status_code != 200:
                print("Telegram send failed:", r.text)
            else:
                print("Telegram sent")

        except Exception as e:
            print("Telegram error:", e)
    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _send_telegram(self, message: str):
        """Attempt real Telegram delivery; fall back to print on error."""
        try:
            import requests  # lazy import — not a hard dependency

            url = self._TELEGRAM_API.format(token=self._token)
            payload = {"chat_id": self._chat_id, "text": message}
            response = requests.post(url, json=payload, timeout=5)

            if not response.ok:
                print(
                    f"[TelegramControlCenter] Delivery failed "
                    f"(HTTP {response.status_code}): {response.text}"
                )
        except ImportError:
            print("[TelegramControlCenter] `requests` not installed — falling back to LOG.")
            print("[TELEGRAM]", message)
        except Exception as exc:
            print(f"[TelegramControlCenter] Unexpected error: {exc}")
            print("[TELEGRAM]", message)

    # ------------------------------------------------------------------
    # Convenience wrappers
    # ------------------------------------------------------------------

    def alert(self, message: str):
        """Send a high-priority alert."""
        self.send(f"🚨 ALERT: {message}")

    def notify(self, message: str):
        """Send a routine notification."""
        self.send(f"ℹ️  {message}")

    def heartbeat(self):
        """Send a system heartbeat ping."""
        self.send("💓 Quant Ecosystem heartbeat OK")

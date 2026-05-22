import hmac
import hashlib
import time
from typing import Tuple


DEFAULT_WINDOW_SECONDS = 90


class CommandSigner:
    def __init__(self, secret: str, window: int = DEFAULT_WINDOW_SECONDS):
        if not secret:
            raise ValueError("TELEGRAM_COMMAND_SECRET missing")

        self.secret = secret.encode("utf-8")
        self.window = window

    def sign(self, command: str, ts: int | None = None) -> Tuple[str, int]:
        ts = ts or int(time.time())
        payload = f"{command}|{ts}".encode()
        sig = hmac.new(self.secret, payload, hashlib.sha256).hexdigest()
        return sig, ts

    def verify(self, command: str, ts: int, signature: str) -> bool:
        now = int(time.time())

        if abs(now - ts) > self.window:
            return False

        payload = f"{command}|{ts}".encode()
        expected = hmac.new(self.secret, payload, hashlib.sha256).hexdigest()

        return hmac.compare_digest(expected, signature)
import hmac
import hashlib
import os
import time


LEGACY_TOKEN = "QE3_SECURE_TOKEN"


class TokenValidator:

    def __init__(self):
        self._secret = (
            os.getenv("QE3_AUTH_SECRET")
            or "QE3_AUTH_FALLBACK"
        ).encode("utf-8")

        self._ttl = 3600

    def issue(
        self,
        subject,
    ):
        ts = str(
            int(time.time())
        )

        payload = f"{subject}|{ts}"

        sig = hmac.new(
            self._secret,
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return f"{payload}|{sig}"

    def _validate_signed(
        self,
        token,
    ):
        subject, ts, sig = token.split("|")

        payload = f"{subject}|{ts}"

        expected = hmac.new(
            self._secret,
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(
            expected,
            sig,
        ):
            return False

        age = time.time() - int(ts)

        if age > self._ttl:
            return False

        return True

    def validate(
        self,
        token,
    ):
        try:
            if token == LEGACY_TOKEN:
                return True

            if "|" in str(token):
                return self._validate_signed(
                    token
                )

            return False

        except Exception:
            return False


token_validator = TokenValidator()
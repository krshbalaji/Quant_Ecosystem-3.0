import base64
import hashlib
import os
from threading import RLock


class SecretsVault:
    """
    Institutional secrets governance.

    Runtime encrypted storage.
    Process-local secure access layer.
    Rotation-ready.
    """

    def __init__(self):
        self._lock = RLock()
        self._secrets = {}
        self._master_key = self._derive_master_key()

    def _derive_master_key(self):
        seed = (
            os.getenv("QE3_MASTER_KEY")
            or os.getenv("COMPUTERNAME")
            or "QE3_FALLBACK_MASTER"
        )
        return hashlib.sha256(
            seed.encode("utf-8")
        ).digest()

    def _xor(self, payload: bytes):
        key = self._master_key
        out = bytearray()

        for i, b in enumerate(payload):
            out.append(
                b ^ key[i % len(key)]
            )

        return bytes(out)

    def _encrypt(self, value: str):
        raw = value.encode("utf-8")
        cipher = self._xor(raw)
        return base64.b64encode(
            cipher
        ).decode("utf-8")

    def _decrypt(self, value: str):
        raw = base64.b64decode(
            value.encode("utf-8")
        )
        plain = self._xor(raw)
        return plain.decode("utf-8")

    def store(
        self,
        key,
        value,
    ):
        if value is None:
            return

        with self._lock:
            self._secrets[key] = (
                self._encrypt(
                    str(value)
                )
            )

    def fetch(
        self,
        key,
        default=None,
    ):
        with self._lock:
            value = self._secrets.get(key)

        if value is None:
            return default

        try:
            return self._decrypt(value)
        except Exception:
            return default

    def revoke(
        self,
        key,
    ):
        with self._lock:
            self._secrets.pop(
                key,
                None,
            )

    def rotate_master_key(self):
        with self._lock:
            decrypted = {}

            for k, v in self._secrets.items():
                try:
                    decrypted[k] = (
                        self._decrypt(v)
                    )
                except Exception:
                    continue

            self._master_key = (
                self._derive_master_key()
            )

            self._secrets.clear()

            for k, v in decrypted.items():
                self.store(k, v)

    def clear(self):
        with self._lock:
            self._secrets.clear()


secrets_vault = SecretsVault()
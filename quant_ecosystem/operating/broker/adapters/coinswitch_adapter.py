"""CoinSwitch REST adapter.

This wrapper keeps integration resilient: if any live call fails, caller can fallback to simulated ledger.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Dict, Optional

import requests


class CoinSwitchAdapter:
    """Minimal signed API adapter for CoinSwitch-like REST interfaces."""

    def __init__(self, api_key: str, api_secret: str, base_url: str, **kwargs):
        self.api_key = (api_key or "").strip()
        self.api_secret = (api_secret or "").strip()
        self.base_url = (base_url or "").rstrip("/")

    def is_ready(self) -> bool:
        return bool(self.api_key and self.api_secret and self.base_url)

    def get(self, path: str, query: Optional[Dict] = None, timeout: int = 8) -> Dict:
        return self._request("GET", path, payload=None, query=query, timeout=timeout)

    def post(self, path: str, payload: Optional[Dict] = None, timeout: int = 8) -> Dict:
        return self._request("POST", path, payload=payload or {}, query=None, timeout=timeout)

    def _request(self, method: str, path: str, payload: Optional[Dict], query: Optional[Dict], timeout: int) -> Dict:
        if not self.is_ready():
            return {"ok": False, "error": "adapter_not_ready"}

        path = path if str(path).startswith("/") else f"/{path}"
        query = query or {}
        body = payload or {}
        ts = str(int(time.time() * 1000))
        serialized = json.dumps(body, separators=(",", ":"), sort_keys=True) if body else ""
        prehash = f"{ts}{method.upper()}{path}{serialized}"
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            prehash.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-API-KEY": self.api_key,
            "X-API-SIGNATURE": signature,
            "X-API-TIMESTAMP": ts,
        }
        url = f"{self.base_url}{path}"

        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=query, timeout=timeout)
            else:
                response = requests.post(url, headers=headers, json=body, timeout=timeout)
            data = response.json()
            if response.status_code >= 400:
                return {"ok": False, "status": response.status_code, "error": data}
            return {"ok": True, "data": data}
        except (requests.RequestException, ValueError) as exc:
            return {"ok": False, "error": str(exc)}

import requests
from config import Config

import os

class Config:
    # existing stuff...

    CLOUD_BASE_URL = os.getenv(
        "CLOUD_BASE_URL",
        "https://quant-ecosystem-shadow-16683273546.asia-south1.run.app"
    )

    @staticmethod
    def get_api_key():
        return os.getenv("API_KEY") or os.getenv("CLOUD_API_KEY")

BASE_URL = Config.CLOUD_BASE_URL


def get_headers():
    return {
        "X-API-KEY": Config.get_api_key(),
        "Content-Type": "application/json"
    }


def get_portfolio():
    try:
        r = requests.get(
            f"{BASE_URL}/portfolio",
            headers=get_headers(),
            timeout=5
        )

        if r.status_code != 200:
            print(f"[CLOUD] Bad response: {r.status_code}")
            return {}

        try:
            return r.json().get("positions", {})
        except Exception:
            print(f"[CLOUD] Non-JSON response: {r.text[:100]}")
            return {}

    except Exception as e:
        print(f"[CLOUD] Fetch portfolio failed: {e}")
        return {}


def update_position(symbol, side, qty):
    try:
        payload = {
            "symbol": symbol,
            "side": side,
            "qty": qty
        }

        requests.post(
            f"{BASE_URL}/portfolio/update",
            json=payload,
            headers=get_headers(),
            timeout=5
        )

    except Exception as e:
        print(f"[CLOUD] Update failed: {e}")
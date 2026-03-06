"""
main.py  (patched boot sequence)
==================================
Quant Ecosystem 3.0 — reference boot entry point.

CHANGES FROM ORIGINAL
─────────────────────
The three lines marked NEW are the only additions needed.
Everything else is your existing boot sequence — unchanged.

Run:
    python main.py              # PAPER mode (default)
    QUANT_MODE=LIVE python main.py
"""

import os
import sys

# ── 0. Determine mode from environment ───────────────────────────────────────
MODE   = os.environ.get("QUANT_MODE", "PAPER").upper()
CONFIG = {
    "mode":              MODE,
    "DAILY_LOSS_LIMIT":  float(os.environ.get("DAILY_LOSS_LIMIT", "-5000")),
    "MAX_DRAWDOWN_PCT":  float(os.environ.get("MAX_DRAWDOWN_PCT",  "-0.05")),
    "STARTING_EQUITY":   float(os.environ.get("STARTING_EQUITY",  "100000")),
    "TELEGRAM_TOKEN":    os.environ.get("TELEGRAM_TOKEN",    ""),
    "TELEGRAM_CHAT_ID":  os.environ.get("TELEGRAM_CHAT_ID",  ""),
    "RESET_CODE":        os.environ.get("RESET_CODE",        ""),
}

print(f"[main] Quant Ecosystem 3.0 booting — mode={MODE}")


def shutdown(reason: str = "Shutdown requested") -> None:
    """Graceful exit hook — called on CRITICAL diagnostic in LIVE mode."""
    print(f"[main] shutdown() called: {reason}")
    sys.exit(1)


import logging

logging.basicConfig(level=logging.INFO)

from quant_ecosystem.core.system_factory import SystemFactory


def main():

    config = {}

    print("[main] Quant Ecosystem 3.0 booting — mode=PAPER")

    factory = SystemFactory(config)

    router = factory.build()

    if router.telegram:
        router.telegram.send("🚀 Quant Ecosystem booted")

    print("Boot completed.")


if __name__ == "__main__":
    main()
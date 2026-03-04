import os
import sys
from pathlib import Path

import requests


class FirstTimeOnboarding:

    def __init__(self, env_path=".env"):
        self.env_path = Path(env_path)

    def ensure(self):
        existing = self._read_env()
        if not sys.stdin.isatty():
            print("Skipping first-time onboarding (non-interactive session).")
            return

        completed = existing.get("ONBOARDING_COMPLETED", "").lower() == "true"
        if completed:
            self._repair_if_needed(existing)
            return

        print("\n=== Quant Ecosystem First-Time Enrollment ===")
        print("Enter details once. They will be saved in .env in KEY=VALUE format.")
        print("You can update them later by editing .env directly.\n")

        mode = self._ask("Mode [PAPER/LIVE]", existing.get("MODE", "PAPER")).upper()
        broker = self._ask("Broker name", existing.get("BROKER_NAME", "FYERS")).upper()

        updates = {
            "MODE": mode,
            "BROKER_NAME": broker,
            "ONBOARDING_COMPLETED": "true",
        }

        if broker == "FYERS":
            print("\nFYERS details guide:")
            print("1) Login to FYERS API Dashboard and create app.")
            print("2) Copy APP_ID, SECRET_KEY, and REDIRECT_URI from app settings.")
            print("3) Generate ACCESS_TOKEN via FYERS auth flow.\n")

            updates["FYERS_APP_ID"] = self._ask("FYERS_APP_ID", existing.get("FYERS_APP_ID", ""))
            updates["FYERS_SECRET_KEY"] = self._ask("FYERS_SECRET_KEY", existing.get("FYERS_SECRET_KEY", ""))
            updates["FYERS_REDIRECT_URI"] = self._ask("FYERS_REDIRECT_URI", existing.get("FYERS_REDIRECT_URI", ""))

            token_label = "FYERS_ACCESS_TOKEN (required for LIVE)" if mode == "LIVE" else "FYERS_ACCESS_TOKEN (optional in PAPER)"
            updates["FYERS_ACCESS_TOKEN"] = self._ask(token_label, existing.get("FYERS_ACCESS_TOKEN", ""))
        elif broker == "COINSWITCH":
            print("\nCoinSwitch details guide:")
            print("1) Open CoinSwitch developer/API settings.")
            print("2) Create API key and secret for trading.")
            print("3) Keep live disabled initially; test in PAPER first.\n")
            updates["COINSWITCH_API_KEY"] = self._ask("COINSWITCH_API_KEY", existing.get("COINSWITCH_API_KEY", ""))
            updates["COINSWITCH_API_SECRET"] = self._ask("COINSWITCH_API_SECRET", existing.get("COINSWITCH_API_SECRET", ""))
            updates["COINSWITCH_BASE_URL"] = self._ask(
                "COINSWITCH_BASE_URL",
                existing.get("COINSWITCH_BASE_URL", "https://api.coinswitch.co"),
            )
            live_default = existing.get("COINSWITCH_ENABLE_LIVE", "false")
            updates["COINSWITCH_ENABLE_LIVE"] = self._ask("COINSWITCH_ENABLE_LIVE [true/false]", live_default).lower()

        use_telegram = self._ask("Enable Telegram alerts? [Y/N]", "Y").upper() == "Y"
        if use_telegram:
            print("\nTelegram details guide:")
            print("1) Open Telegram and message @BotFather.")
            print("2) Run /newbot and copy TELEGRAM_TOKEN.")
            print("3) Send /start to your new bot from your Telegram account.")
            print("4) TELEGRAM_CHAT_ID is numeric only (example: 123456789 or -1001234567890).")
            print("   Do NOT paste bot token as chat id.\n")

            token_default = existing.get("TELEGRAM_TOKEN") or existing.get("TELEGRAM_BOT_TOKEN", "")
            updates["TELEGRAM_TOKEN"] = self._ask("TELEGRAM_TOKEN", token_default)

            entered_chat = self._ask("TELEGRAM_CHAT_ID (leave blank for auto-detect)", existing.get("TELEGRAM_CHAT_ID", ""))
            if not entered_chat:
                detected = self._detect_chat_id(updates["TELEGRAM_TOKEN"])
                if detected:
                    print(f"Auto-detected TELEGRAM_CHAT_ID: {detected}")
                    entered_chat = detected
                else:
                    print("Auto-detect failed. Keep app running, send /start to your bot, then update .env with numeric chat id.")

            if entered_chat and not self._is_valid_chat_id(entered_chat):
                print("Invalid TELEGRAM_CHAT_ID format detected. Clearing it now.")
                entered_chat = ""

            updates["TELEGRAM_CHAT_ID"] = entered_chat

        updates["TRADE_SYMBOLS"] = self._ask(
            "TRADE_SYMBOLS (comma-separated)",
            existing.get("TRADE_SYMBOLS", "NSE:SBIN-EQ,NSE:RELIANCE-EQ,NSE:INFY-EQ"),
        )

        merged = {**existing, **updates}
        self._write_env(merged)

        for key, value in updates.items():
            os.environ[key] = value

        print("\nEnrollment completed. Config saved to .env.\n")

    def _repair_if_needed(self, existing):
        token = existing.get("TELEGRAM_TOKEN") or existing.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = existing.get("TELEGRAM_CHAT_ID", "")
        if not token:
            return
        if self._is_valid_chat_id(chat_id):
            return

        print("\nTelegram configuration check:")
        print("TELEGRAM_CHAT_ID is missing or invalid.")
        fix = self._ask("Do you want to repair Telegram setup now? [Y/N]", "Y").upper() == "Y"
        if not fix:
            return

        print("Send /start to your bot first, then continue.")
        entered_chat = self._ask("TELEGRAM_CHAT_ID (leave blank for auto-detect)", "")
        if not entered_chat:
            detected = self._detect_chat_id(token)
            if detected:
                print(f"Auto-detected TELEGRAM_CHAT_ID: {detected}")
                entered_chat = detected

        if not self._is_valid_chat_id(entered_chat):
            print("Still invalid. Telegram alerts will stay disabled until corrected.")
            return

        existing["TELEGRAM_CHAT_ID"] = entered_chat
        self._write_env(existing)
        os.environ["TELEGRAM_CHAT_ID"] = entered_chat
        print("Telegram configuration repaired.\n")

    def _ask(self, label, default=""):
        suffix = f" [{default}]" if default else ""
        value = input(f"{label}{suffix}: ").strip()
        return value or default

    def _detect_chat_id(self, token):
        if not token:
            return ""

        url = f"https://api.telegram.org/bot{token}/getUpdates"
        try:
            response = requests.get(url, timeout=8)
            payload = response.json()
        except (requests.RequestException, ValueError):
            return ""

        if not payload.get("ok"):
            return ""

        for item in reversed(payload.get("result", [])):
            message = item.get("message", {})
            chat_id = str(message.get("chat", {}).get("id", "")).strip()
            if self._is_valid_chat_id(chat_id):
                return chat_id

        return ""

    def _is_valid_chat_id(self, chat_id):
        value = str(chat_id).strip()
        if not value:
            return False
        if ":" in value:
            return False
        if value.startswith("-"):
            return value[1:].isdigit()
        return value.isdigit()

    def _read_env(self):
        if not self.env_path.exists():
            return {}

        data = {}
        for line in self.env_path.read_text(encoding="utf-8").splitlines():
            clean = line.strip()
            if not clean or clean.startswith("#") or "=" not in clean:
                continue
            key, value = clean.split("=", 1)
            data[key.strip()] = value.strip()
        return data

    def _write_env(self, values):
        ordered_keys = [
            "BROKER_NAME",
            "MODE",
            "FYERS_APP_ID",
            "FYERS_SECRET_KEY",
            "FYERS_REDIRECT_URI",
            "FYERS_ACCESS_TOKEN",
            "COINSWITCH_API_KEY",
            "COINSWITCH_API_SECRET",
            "COINSWITCH_BASE_URL",
            "COINSWITCH_ENABLE_LIVE",
            "TELEGRAM_TOKEN",
            "TELEGRAM_CHAT_ID",
            "TRADE_SYMBOLS",
            "MAX_DAILY_LOSS_PCT",
            "MAX_POSITION_SIZE_PCT",
            "MAX_PORTFOLIO_EXPOSURE_PCT",
            "MAX_SYMBOL_EXPOSURE_PCT",
            "COOLDOWN_AFTER_LOSS",
            "BROKER_FEE_BPS",
            "BASE_SLIPPAGE_BPS",
            "MAX_SLIPPAGE_BPS",
            "ONBOARDING_COMPLETED",
        ]

        lines = []
        seen = set()
        for key in ordered_keys:
            if key in values:
                lines.append(f"{key}={values[key]}")
                seen.add(key)

        for key in sorted(values.keys()):
            if key in seen:
                continue
            lines.append(f"{key}={values[key]}")

        self.env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

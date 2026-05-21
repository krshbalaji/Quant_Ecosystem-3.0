"""
QE3 Security Governor.

Centralized security controls for execution-facing infrastructure.
"""

from __future__ import annotations

import os
from typing import Optional


class SecurityGovernor:
    REQUIRED_LIVE_SECRETS = (
        "TRADINGVIEW_WEBHOOK_SECRET",
        "QE3_TELEGRAM_APPROVAL_TOKEN",
    )

    FORBIDDEN_VALUES = {
        "",
        "QE3_SECRET",
        "QE3_APPROVE",
        "CHANGE_ME",
        "DEFAULT",
    }

    @classmethod
    def is_kill_switch_active(cls) -> bool:
        value = str(os.getenv("GLOBAL_KILL_SWITCH", "false")).strip().lower()
        return value in {"1", "true", "yes", "on"}

    @classmethod
    def get_telegram_approval_token(cls) -> str:
        token = str(os.getenv("QE3_TELEGRAM_APPROVAL_TOKEN", "")).strip()

        if token in cls.FORBIDDEN_VALUES:
            raise RuntimeError(
                "QE3_TELEGRAM_APPROVAL_TOKEN missing or insecure."
            )

        return token

    @classmethod
    def get_tradingview_webhook_secret(cls) -> str:
        secret = str(os.getenv("TRADINGVIEW_WEBHOOK_SECRET", "")).strip()

        if secret in cls.FORBIDDEN_VALUES:
            raise RuntimeError(
                "TRADINGVIEW_WEBHOOK_SECRET missing or insecure."
            )

        return secret

    @classmethod
    def validate_security_configuration(
        cls,
        mode: Optional[str] = None,
    ) -> None:
        mode_value = str(mode or os.getenv("BROKER_MODE", "PAPER")).strip().upper()

        if mode_value in {"LIVE", "REAL"}:
            for secret_name in cls.REQUIRED_LIVE_SECRETS:
                value = str(os.getenv(secret_name, "")).strip()

                if value in cls.FORBIDDEN_VALUES:
                    raise RuntimeError(
                        f"Missing or insecure required secret: {secret_name}"
                    )
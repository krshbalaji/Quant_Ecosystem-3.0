"""
quant_ecosystem/communication/__init__.py

Communication and control layer for Quant Ecosystem 3.0.
"""

from __future__ import annotations

__version__ = "1.0.0"

try:
    from .telegram_control_center import (
        TelegramControlCenter,
        CommandResult,
    )
    from .telegram_commands import (
        CommandParser,
        CommandValidator,
        CommandFormatter,
        CommandType,
        CommandSchema,
        ParseResult,
    )
    from .telegram_notifier import (
        TelegramNotifier,
        Notification,
        AlertLevel,
    )
    from .telegram_bot import QuantTelegramBot
    
    __all__ = [
        "TelegramControlCenter",
        "CommandResult",
        "CommandParser",
        "CommandValidator",
        "CommandFormatter",
        "CommandType",
        "CommandSchema",
        "ParseResult",
        "TelegramNotifier",
        "Notification",
        "AlertLevel",
        "QuantTelegramBot",
    ]

except ImportError as exc:
    import logging
    logger = logging.getLogger(__name__)
    logger.warning("Failed to import communication modules: %s", exc)
    __all__ = []

"""Telegram bot wrapper for secure remote command center.

Requires `python-telegram-bot` (v20+).
"""

from __future__ import annotations

from typing import Optional

from telegram import Update
from telegram.ext import Application, CommandHandler as TgCommandHandler, ContextTypes, MessageHandler, filters

from quant_ecosystem.telegram_control.command_handler import CommandHandler


class QuantTelegramBot:
    """Remote Telegram control bot with authorization gate."""

    def __init__(self, token: str, command_handler: CommandHandler):
        self.token = (token or "").strip()
        self.command_handler = command_handler
        self.app: Optional[Application] = None

    def build(self) -> "QuantTelegramBot":
        if not self.token:
            raise ValueError("Telegram token missing.")
        self.app = Application.builder().token(self.token).build()

        self.app.add_handler(TgCommandHandler("status", self._on_command))
        self.app.add_handler(TgCommandHandler("pause", self._on_command))
        self.app.add_handler(TgCommandHandler("resume", self._on_command))
        self.app.add_handler(TgCommandHandler("activate_strategy", self._on_command))
        self.app.add_handler(TgCommandHandler("deactivate_strategy", self._on_command))
        self.app.add_handler(TgCommandHandler("allocate_capital", self._on_command))
        self.app.add_handler(TgCommandHandler("system_health", self._on_command))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_plain_text))
        return self

    async def start(self) -> None:
        if self.app is None:
            self.build()
        assert self.app is not None
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()

    async def stop(self) -> None:
        if self.app is None:
            return
        await self.app.updater.stop()
        await self.app.stop()
        await self.app.shutdown()

    async def _on_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_message or not update.effective_user:
            return
        text = str(update.effective_message.text or "").strip()
        user_id = str(update.effective_user.id)
        reply = self.command_handler.handle(text, user_id=user_id)
        await update.effective_message.reply_text(reply)

    async def _on_plain_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_message or not update.effective_user:
            return
        text = str(update.effective_message.text or "").strip()
        if not text.startswith("/"):
            text = "/" + text
        user_id = str(update.effective_user.id)
        reply = self.command_handler.handle(text, user_id=user_id)
        await update.effective_message.reply_text(reply)


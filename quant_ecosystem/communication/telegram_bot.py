from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any, List, Optional

from quant_ecosystem.communication.telegram_commands import CommandFormatter

try:
    from telegram import Chat, Update
    from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

    TELEGRAM_AVAILABLE = True
except ImportError:
    Chat = Update = ContextTypes = None  # type: ignore[assignment]
    Application = CommandHandler = MessageHandler = filters = None  # type: ignore[assignment]
    TELEGRAM_AVAILABLE = False

logger = logging.getLogger(__name__)


class QuantTelegramBot:
    def __init__(
        self,
        token: str,
        control_center: Any,
        default_chat_id: Optional[int] = None,
        authorized_users: Optional[List[str]] = None,
        authorized_chats: Optional[List[int]] = None,
    ) -> None:
        if not TELEGRAM_AVAILABLE:
            raise ImportError("python-telegram-bot is not installed")

        self.token = str(token or "").strip()
        if not self.token:
            raise ValueError("Telegram token cannot be empty")

        self.control_center = control_center
        self.default_chat_id = int(default_chat_id) if default_chat_id is not None else None
        self.authorized_users = {str(user_id) for user_id in (authorized_users or [])}
        self.authorized_chats = {int(chat_id) for chat_id in (authorized_chats or [])}
        if self.default_chat_id is not None:
            self.authorized_chats.add(self.default_chat_id)

        self.app: Optional[Application] = None
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_signal = threading.Event()
        logger.info("[telegram] bot initialized")

    async def start(self) -> None:
        if self._running:
            return

        self.app = Application.builder().token(self.token).build()
        self._register_handlers()
        await self.app.initialize()
        await self.app.start()
        if self.app.updater is not None:
            #await self.app.updater.start_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)
            self._running = True
        logger.info("[telegram] bot polling started")

    async def stop(self) -> None:
        if not self._running or self.app is None:
            return

        if self.app.updater is not None:
            await self.app.updater.stop()
        await self.app.stop()
        await self.app.shutdown()
        self._running = False
        logger.info("[telegram] bot stopped")

    def start_in_background(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return

        def _runner() -> None:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                self._loop = loop
                loop.run_until_complete(self._background_main())
            except Exception as exc:
                logger.warning("[telegram] bot background start failed: %s", exc)
            finally:
                self._loop = None

        self._thread = threading.Thread(target=_runner, name="QuantTelegramBot", daemon=True)
        self._thread.start()

    def stop_in_background(self, timeout: float = 5.0) -> None:
        self._stop_signal.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)

    def send_message(self, text: str, chat_id: Optional[int] = None) -> bool:
        target_chat_id = int(chat_id) if chat_id is not None else self.default_chat_id
        if target_chat_id is None:
            logger.debug("[telegram] no default chat configured; dropping outbound message")
            return False

        if self.app is None or self.app.bot is None or self._loop is None:
            logger.debug("[telegram] bot not ready; dropping outbound message")
            return False

        async def _send() -> None:
            for page in CommandFormatter.paginate(str(text), max_length=4000):
                await self.app.bot.send_message(chat_id=target_chat_id, text=page)

        try:
            asyncio.run_coroutine_threadsafe(_send(), self._loop)
            return True
        except Exception as exc:
            logger.warning("[telegram] outbound send failed: %s", exc)
            return False

    def send_to_default_chat(self, text: str) -> bool:
        return self.send_message(text=text)

    def _register_handlers(self) -> None:
        if self.app is None:
            return

        commands = [
            "status",
            "start",
            "stop",
            "pause",
            "resume",
            "positions",
            "pnl",
            "strategies",
            "research",
            "shutdown",
            "help",
        ]
        for command in commands:
            self.app.add_handler(CommandHandler(command, self._on_command))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_text))

    async def _on_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.effective_user:
            return
        if not self._is_authorized(str(update.effective_user.id), update.effective_chat):
            await update.message.reply_text("Unauthorized")
            return

        text = str(update.message.text or "").strip()
        result = self.control_center.execute(text, user_id=str(update.effective_user.id))
        await self._reply(update.message.chat_id, result.message)

    async def _on_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.effective_user:
            return
        if not self._is_authorized(str(update.effective_user.id), update.effective_chat):
            return

        text = str(update.message.text or "").strip()
        if not text.startswith("/"):
            text = f"/{text}"
        result = self.control_center.execute(text, user_id=str(update.effective_user.id))
        await self._reply(update.message.chat_id, result.message)

    def _is_authorized(self, user_id: str, chat: Optional[Chat] = None) -> bool:
        if not self.authorized_users and not self.authorized_chats:
            return True
        if user_id in self.authorized_users:
            return True
        if chat is not None and int(chat.id) in self.authorized_chats:
            return True
        return False

    async def _reply(self, chat_id: int, text: str) -> None:
        if self.app is None or self.app.bot is None:
            return
        for page in CommandFormatter.paginate(str(text), max_length=4000):
            await self.app.bot.send_message(chat_id=chat_id, text=page)

    async def _background_main(self) -> None:
        self._stop_signal.clear()
        await self.start()
        try:
            while not self._stop_signal.is_set():
                await asyncio.sleep(1.0)
        finally:
            await self.stop()

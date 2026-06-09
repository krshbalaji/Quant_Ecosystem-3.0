"""
telegram_bot.py — Quant Ecosystem 3.0
======================================

Telegram bot implementation with full integration.

Features:
- Async event handling with python-telegram-bot
- Command routing to TelegramControlCenter
- User authorization and rate limiting
- Error handling and logging
- Graceful shutdown
- Webhook and polling modes

Requires: python-telegram-bot>=20.0

Usage:
    >>> bot = QuantTelegramBot(
    ...     token=os.getenv("TELEGRAM_BOT_TOKEN"),
    ...     control_center=center,
    ...     authorized_users=["123456789", "987654321"]
    ... )
    >>> await bot.start()
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional, List, Dict, Any, TYPE_CHECKING

try:
    from telegram import Update, Chat
    from telegram.ext import (
        Application,
        CommandHandler,
        MessageHandler,
        ContextTypes,
        filters,
    )
    TELEGRAM_AVAILABLE = True

except ImportError:
    TELEGRAM_AVAILABLE = False

if TYPE_CHECKING:
    from telegram import Update, Chat
    from telegram.ext import (
        Application,
        CommandHandler,
        MessageHandler,
        ContextTypes,
        filters,
    )  

    logging.warning(
        "python-telegram-bot not installed. Telegram support disabled."
    )

logger = logging.getLogger(__name__)


class QuantTelegramBot:
    """
    Telegram bot for Quant Ecosystem 3.0 control.
    
    Provides:
    - Remote command execution
    - Real-time notifications
    - System monitoring
    - Strategy management
    - Risk control
    
    Parameters
    ----------
    token : str
        Telegram bot token (from BotFather)
    control_center : TelegramControlCenter
        Reference to control center
    authorized_users : list, optional
        Telegram user IDs with access. If None, all allowed.
    authorized_chats : list, optional
        Telegram chat IDs with access.
    webhook_url : str, optional
        Webhook URL for updates (if using webhook mode)
    polling : bool, default=True
        Use polling instead of webhook
    
    Examples
    --------
    >>> from quant_ecosystem.communication import (
    ...     QuantTelegramBot,
    ...     TelegramControlCenter,
    ...     TelegramNotifier,
    ... )
    >>> 
    >>> # Initialize
    >>> control_center = TelegramControlCenter(
    ...     system_router=router,
    ...     autonomous_loop=research_loop,
    ...     alpha_bank=bank,
    ... )
    >>> 
    >>> notifier = TelegramNotifier(send_callback=send_message)
    >>> 
    >>> bot = QuantTelegramBot(
    ...     token="YOUR_BOT_TOKEN",
    ...     control_center=control_center,
    ...     authorized_users=["123456789"],
    ... )
    >>> 
    >>> # Start bot
    >>> await bot.start()
    >>> 
    >>> # Send notification
    >>> notifier.notify_strategy_discovered(
    ...     strategy_id="strat_001",
    ...     fitness=0.85
    ... )
    """
    
    def __init__(
        self,
        token: str,
        control_center: Any,
        authorized_users: Optional[List[str]] = None,
        authorized_chats: Optional[List[int]] = None,
        webhook_url: Optional[str] = None,
        polling: bool = True,
    ) -> None:
        if not TELEGRAM_AVAILABLE:
            raise ImportError("python-telegram-bot not installed. Install with: pip install python-telegram-bot")
        
        self.token = str(token).strip()
        if not self.token:
            raise ValueError("Telegram token cannot be empty")
        
        self.control_center = control_center
        self.authorized_users = set(str(uid) for uid in (authorized_users or []))
        self.authorized_chats = set(authorized_chats or [])
        self.webhook_url = webhook_url
        self.polling = polling
        
        self.app: Optional[Application] = None
        self._running = False
        
        logger.info(
            "QuantTelegramBot initialized "
            "(authorized_users=%d, authorized_chats=%d, mode=%s)",
            len(self.authorized_users),
            len(self.authorized_chats),
            "webhook" if webhook_url else "polling"
        )
    
    # -----------------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------------
    
    async def start(self) -> None:
        """Start the bot."""
        try:
            if self._running:
                logger.warning("Bot already running")
                return
            
            # Build application
            self.app = Application.builder().token(self.token).build()
            
            # Register handlers
            self._register_handlers()
            
            # Initialize
            await self.app.initialize()
            await self.app.start()
            
            self._running = True
            
            updater = self.app.updater

            if updater is None:
                raise RuntimeError("Telegram updater unavailable")

          
            if self.polling:
                # Start polling
                logger.info("Starting bot with polling mode")
                await updater.start_polling()
                
            else:
                # Webhook mode
                logger.info("Starting bot with webhook mode: %s", self.webhook_url)
                if self.webhook_url:
                    updater = self.app.updater

                    if updater is None:
                        raise RuntimeError("Telegram updater unavailable")
                    await updater.start_webhook(
                        listen="0.0.0.0",
                        port=8080,
                        url_path=self.token,
                        webhook_url=self.webhook_url,
                    )
            
            logger.info("QuantTelegramBot started successfully")
        
        except Exception as exc:
            logger.error("Failed to start bot: %s", exc)
            raise
    
    async def stop(self) -> None:
        """Stop the bot gracefully."""
        try:
            if not self._running or not self.app:
                return
            
            logger.info("Stopping QuantTelegramBot...")
            
            updater = self.app.updater

            if updater is not None:
                await updater.stop()
            await self.app.stop()
            await self.app.shutdown()
            
            self._running = False
            logger.info("QuantTelegramBot stopped")
        
        except Exception as exc:
            logger.error("Error stopping bot: %s", exc)
    
    # -----------------------------------------------------------------------
    # Handlers
    # -----------------------------------------------------------------------
    
    def _register_handlers(self) -> None:
        """Register command handlers."""
        if not self.app:
            return
        
        # Command handlers
        commands = [
            "status", "research_progress", "top_strategies", "portfolio",
            "pause_research", "resume_research", "strategy_metrics",
            "system_health", "research_stats", "allocate", "help",
        ]
        
        for command in commands:
            self.app.add_handler(CommandHandler(command, self._on_command))
        
        # Fallback for text messages
        self.app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_text)
        )
        
        logger.debug("Registered %d command handlers", len(commands))
    
    async def _on_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle command."""
        try:
            if not update.message or not update.effective_user:
                return
            
            # Check authorization
            user_id = str(update.effective_user.id)
            if not self._is_authorized(user_id, update.effective_chat):
                message = update.message

                if message is None:
                    return
                await update.message.reply_text(
                    "🚫 You are not authorized to use this bot.\n"
                    "Contact the administrator for access."
                )
                logger.warning("Unauthorized access attempt from user %s", user_id)
                return
            
            # Get command
            text = str(update.message.text or "").strip()
            
            # Parse command
            parts = text.lstrip("/").split(maxsplit=1)
            command = parts[0].lower()
            args = parts[1].split() if len(parts) > 1 else []
            
            logger.info("Command from %s: /%s %s", user_id, command, " ".join(args))
            
            # Execute command
            result = self.control_center.execute(
                command=f"/{command}",
                user_id=user_id,
                args=args,
            )
            
            # Format response
            if result.success:
                response = result.message
            else:
                response = result.message or "❌ Command failed"
            
            # Send response (paginate if too long)
            await self._send_message(update.message.chat_id, response)
        
        except Exception as exc:
            logger.error("Command handler error: %s", exc)
            try:
                message = update.message

                if message is None:
                    return

                await message.reply_text(
                    f"❌ Error: {str(exc)[:100]}"
                )
            except Exception:
                pass
    
    async def _on_text(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle text message (non-command)."""
        try:
            if not update.message or not update.effective_user:
                return
            
            # Check authorization
            user_id = str(update.effective_user.id)
            if not self._is_authorized(user_id, update.effective_chat):
                return
            
            # Try to parse as command
            text = str(update.message.text or "").strip()
            if not text.startswith("/"):
                text = "/" + text
            
            # Re-route to command handler
            parts = text.lstrip("/").split(maxsplit=1)
            command = parts[0].lower()
            args = parts[1].split() if len(parts) > 1 else []
            
            result = self.control_center.execute(
                command=f"/{command}",
                user_id=user_id,
                args=args,
            )
            
            response = result.message if result.success else result.message or "❌ Unknown command"
            
            await self._send_message(update.message.chat_id, response)
        
        except Exception as exc:
            logger.debug("Text handler error: %s", exc)
    
    # -----------------------------------------------------------------------
    # Utilities
    # -----------------------------------------------------------------------
    
    def _is_authorized(
        self,
        user_id: str,
        chat: Optional[Chat] = None,
    ) -> bool:
        """Check if user is authorized."""
        # No restrictions if empty
        if not self.authorized_users and not self.authorized_chats:
            return True
        
        # Check user
        if user_id in self.authorized_users:
            return True
        
        # Check chat
        if chat and chat.id in self.authorized_chats:
            return True
        
        return False
    
    async def _send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str = "Markdown",
    ) -> None:
        """Send message with pagination."""
        try:
            if not self.app or not self.app.bot:
                logger.error("Bot not initialized")
                return
            
            # Paginate if needed (4096 char limit)
            max_length = 4000
            if len(text) <= max_length:
                await self.app.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode=parse_mode,
                )
            else:
                # Split into pages
                lines = text.split("\n")
                pages = []
                current = ""
                
                for line in lines:
                    if len(current) + len(line) + 1 > max_length:
                        if current:
                            pages.append(current)
                        current = line
                    else:
                        current += ("\n" if current else "") + line
                
                if current:
                    pages.append(current)
                
                # Send each page
                for i, page in enumerate(pages):
                    prefix = f"[Page {i+1}/{len(pages)}]\n" if len(pages) > 1 else ""
                    await self.app.bot.send_message(
                        chat_id=chat_id,
                        text=prefix + page,
                        parse_mode=parse_mode,
                    )
                    
                    # Rate limit
                    if i < len(pages) - 1:
                        await asyncio.sleep(0.5)
        
        except Exception as exc:
            logger.error("Failed to send message: %s", exc)
    
    async def send_notification(
        self,
        chat_id: int,
        notification_text: str,
        parse_mode: str = "Markdown",
    ) -> bool:
        """Send notification message."""
        try:
            await self._send_message(chat_id, notification_text, parse_mode)
            return True
        except Exception as exc:
            logger.error("Failed to send notification: %s", exc)
            return False

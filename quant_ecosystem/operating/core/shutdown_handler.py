"""
Global shutdown handler for graceful system termination.

Provides a centralized point for all system components to check
if shutdown has been requested, and implements clean cancellation
of all async tasks and threads.
"""

import asyncio
import logging
import signal
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


class ShutdownHandler:
    """Manages graceful system shutdown across all async loops."""

    def __init__(self):
        self.running: bool = True
        self._shutdown_event: Optional[asyncio.Event] = None
        self._callbacks: List[Callable] = []
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def is_running(self) -> bool:
        """Check if system should continue running."""
        return self.running

    def request_shutdown(self, reason: str = "Shutdown requested") -> None:
        """Request graceful shutdown."""
        logger.info("🛑 Shutdown requested: %s", reason)
        self.running = False
        if self._shutdown_event:
            self._shutdown_event.set()

    def add_callback(self, callback: Callable) -> None:
        """Register a callback to invoke during shutdown."""
        self._callbacks.append(callback)

    async def setup_signal_handlers(self) -> None:
        """Setup OS signal handlers for Ctrl+C and system signals."""
        loop = asyncio.get_running_loop()
        self._loop = loop
        self._shutdown_event = asyncio.Event()

        def signal_handler(signum, frame):
            sig_name = signal.Signals(signum).name
            logger.warning("Signal received: %s", sig_name)
            self.request_shutdown(f"OS signal {sig_name}")

        try:
            loop.add_signal_handler(signal.SIGINT, signal_handler, signal.SIGINT, None)
            loop.add_signal_handler(signal.SIGTERM, signal_handler, signal.SIGTERM, None)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            pass

    async def wait_for_shutdown(self) -> None:
        """Wait until shutdown is requested."""
        if self._shutdown_event:
            await self._shutdown_event.wait()

    async def invoke_callbacks(self) -> None:
        """Invoke all registered shutdown callbacks."""
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as exc:
                logger.exception("Shutdown callback failed: %s", exc)

    def __repr__(self) -> str:
        return f"ShutdownHandler(running={self.running})"


# Global singleton instance
_shutdown_handler: Optional[ShutdownHandler] = None


def get_shutdown_handler() -> ShutdownHandler:
    """Get or create the global shutdown handler."""
    global _shutdown_handler
    if _shutdown_handler is None:
        _shutdown_handler = ShutdownHandler()
    return _shutdown_handler


def is_running() -> bool:
    """Check if system should continue running."""
    return get_shutdown_handler().is_running()


def request_shutdown(reason: str = "Shutdown requested") -> None:
    """Request graceful shutdown."""
    get_shutdown_handler().request_shutdown(reason)

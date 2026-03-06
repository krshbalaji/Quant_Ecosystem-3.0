"""
Quant Ecosystem 3.0 — Boot Entry Point
=======================================
Single, deterministic entry point for all operating modes.
No runtime dependency installation. No git auto-pull.
Structured logging only. No prints.

Usage:
    MODE=RESEARCH python main.py
    MODE=PAPER    python main.py
    MODE=LIVE     python main.py
"""

from __future__ import annotations

import asyncio
import logging
import logging.handlers
import os
import signal
import sys
from pathlib import Path

# ── Resolve project root ──────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


# ─────────────────────────────────────────────────────────────────────────────
# Logging — configured BEFORE any application import
# ─────────────────────────────────────────────────────────────────────────────

def _configure_logging() -> logging.Logger:
    """
    Configure structured, production-grade logging.

    * Console handler   – human-readable, INFO+
    * Rotating file     – JSON-friendly, DEBUG+ (logs/quant_ecosystem.log)
    * Root logger level – DEBUG so handlers control their own floor

    Returns the root 'quant_ecosystem' logger for boot-phase messages.
    """
    log_dir = _ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Remove any pre-existing handlers (e.g. from library imports)
    root_logger.handlers.clear()

    fmt_detailed = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)-40s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    fmt_console = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )

    # — Console handler (INFO+) ────────────────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(fmt_console)

    # — Rotating file handler (DEBUG+, 10 MB × 5 files) ──────────────────────
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "quant_ecosystem.log",
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt_detailed)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Suppress noisy third-party loggers
    for noisy in ("urllib3", "asyncio", "fyers_apiv3", "websocket", "uvicorn.error"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    return logging.getLogger("quant_ecosystem")


_log = _configure_logging()


# ─────────────────────────────────────────────────────────────────────────────
# Application imports — AFTER logging is wired
# ─────────────────────────────────────────────────────────────────────────────

def _import_application() -> tuple:
    """
    Lazy, guarded import of application modules.

    Raises SystemExit with an informative message if any critical
    dependency is missing, rather than letting an unhandled ImportError
    propagate with a cryptic stack trace.
    """
    try:
        from quant_ecosystem.core.config_loader import Config  # noqa: PLC0415
        from quant_ecosystem.core.master_orchestrator import MasterOrchestrator  # noqa: PLC0415
        from quant_ecosystem.core.system_factory import SystemFactory  # noqa: PLC0415
    except ImportError as exc:
        _log.critical(
            "Critical import failure — ensure all dependencies are installed "
            "and the project root is on PYTHONPATH. Error: %s",
            exc,
            exc_info=True,
        )
        sys.exit(1)

    return Config, MasterOrchestrator, SystemFactory


# ─────────────────────────────────────────────────────────────────────────────
# Graceful shutdown helpers
# ─────────────────────────────────────────────────────────────────────────────

def _attach_signal_handlers(loop: asyncio.AbstractEventLoop, shutdown_event: asyncio.Event) -> None:
    """
    Register SIGINT / SIGTERM handlers that set a shared shutdown_event
    so the main coroutine can tear down cleanly instead of being killed.
    """
    def _handle(sig_name: str) -> None:
        _log.warning("Received signal %s — initiating graceful shutdown.", sig_name)
        loop.call_soon_threadsafe(shutdown_event.set)

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle, sig.name)
        except (NotImplementedError, RuntimeError):
            # Windows does not support loop.add_signal_handler for all signals
            signal.signal(sig, lambda s, _: _handle(signal.Signals(s).name))


# ─────────────────────────────────────────────────────────────────────────────
# Boot sequence
# ─────────────────────────────────────────────────────────────────────────────

async def _boot(
    Config,       # noqa: N803
    MasterOrchestrator,  # noqa: N803
    SystemFactory,       # noqa: N803
    shutdown_event: asyncio.Event,
) -> int:
    """
    Deterministic, three-phase boot:

        1. Configuration  — load and validate environment config
        2. Assembly       — wire all subsystems for the requested mode
        3. Execution      — run the master orchestrator event loop

    Returns an integer exit code (0 = success, 1 = error).
    """
    # ── Phase 1: Configuration ────────────────────────────────────────────────
    _log.info("=" * 70)
    _log.info("Quant Ecosystem 3.0 — Boot sequence starting")
    _log.info("=" * 70)

    try:
        config = Config()
    except Exception:
        _log.critical("Configuration load failed.", exc_info=True)
        return 1

    mode = str(getattr(config, "mode", "PAPER")).upper()
    _log.info("Operating mode     : %s", mode)
    _log.info("Operation mode     : %s", getattr(config, "operation_mode", "AUTONOMOUS"))
    _log.info("Broker             : %s", getattr(config, "broker_name", "N/A") or "N/A")
    _log.info("Trade symbols      : %s", getattr(config, "trade_symbols", []))

    # ── Phase 2: Assembly ─────────────────────────────────────────────────────
    _log.info("Assembling system components for mode=%s …", mode)

    try:
        factory = SystemFactory(config)
        router  = factory.build()
    except Exception:
        _log.critical("System assembly failed.", exc_info=True)
        return 1

    _log.info("System assembly complete.")

    # ── Phase 3: Execution ────────────────────────────────────────────────────
    _log.info("Handing control to MasterOrchestrator.")

    try:
        orchestrator = MasterOrchestrator(router)
        await orchestrator.start(
            router,
            git_sync=None,        # Git auto-sync removed from boot path
            auto_push_end=False,  # No automated git push
            auto_tag_end=False,   # No automated git tag
        )
    except asyncio.CancelledError:
        _log.info("Orchestrator cancelled — shutdown in progress.")
    except Exception:
        _log.exception("Unhandled exception in MasterOrchestrator.")
        return 1

    _log.info("Session complete. Exiting cleanly.")
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    Config, MasterOrchestrator, SystemFactory = _import_application()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    shutdown_event = asyncio.Event()
    _attach_signal_handlers(loop, shutdown_event)

    exit_code: int = 1
    try:
        exit_code = loop.run_until_complete(
            _boot(Config, MasterOrchestrator, SystemFactory, shutdown_event)
        )
    except KeyboardInterrupt:
        _log.info("KeyboardInterrupt received — exiting.")
        exit_code = 0
    finally:
        # Cancel any lingering tasks
        pending = asyncio.all_tasks(loop)
        if pending:
            _log.debug("Cancelling %d pending task(s) …", len(pending))
            for task in pending:
                task.cancel()
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
        _log.info("Event loop closed. Exit code: %d", exit_code)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()

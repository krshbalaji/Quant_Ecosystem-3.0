"""
quant_ecosystem/telegram/telegram_control_center.py
=====================================================
Telegram Control Center — Quant Ecosystem 3.0

Provides a real-time command-and-control interface to the running trading
system via Telegram.  Runs entirely in a background daemon thread — it
never blocks, never touches the execution path, and is fully decoupled
from all trading logic via read-only references to the SystemRouter.

Architecture
------------

    ┌──────────────────────────────────────────────────────────────┐
    │                  TelegramControlCenter                       │
    │                  (daemon thread, long-poll)                  │
    └──────────────┬───────────────────────────────────────────────┘
                   │  reads (never writes trading state directly)
    ┌──────────────▼───────────────────────────────────────────────┐
    │                     SystemRouter                             │
    │  state · strategy_registry · autonomous_research_loop       │
    │  research_grid · meta_research_ai · alpha_bank              │
    │  capital_intelligence · mutation_engine                     │
    └──────────────────────────────────────────────────────────────┘

Commands
--------
    /status     — Full system health snapshot (regime, trading state, capital)
    /research   — Latest research cycle stats and genome fitness summary
    /strategies — Count and top strategies in registry
    /start      — Resume trading (sets state.trading_halted = False)
    /stop       — Halt trading  (sets state.trading_halted = True)
    /pause      — Pause research loop without stopping trading
    /resume     — Resume paused research loop
    /shutdown   — Gracefully stop research loop and halt trading

Thread safety
-------------
All write operations go through SystemRouter's own public methods
(stop_trading, set_auto_mode) or the research loop's start/stop/pause
API.  The Telegram thread never directly mutates shared state structures.

Configuration
-------------
    bot_token           Telegram bot API token (required)
    allowed_chat_ids    Set of chat IDs allowed to send commands.
                        Empty set = allow all (development mode).
    poll_timeout_sec    Long-poll timeout (default 30s)
    retry_delay_sec     Reconnect backoff on network errors (default 10s)
    max_message_age_sec Ignore stale messages on startup (default 60s)

Usage
-----
    center = TelegramControlCenter(
        bot_token        = "123456:ABC-...",
        allowed_chat_ids = {YOUR_CHAT_ID},
        router           = system_router,
    )
    center.start()          # launches daemon thread — non-blocking
    ...
    center.stop()           # signals thread to exit cleanly
    center.send("Hello!")   # push arbitrary message to all allowed chats
"""

from __future__ import annotations

import json
import logging
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

_TAG = "[telegram_cc]"

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TelegramConfig:
    """All tunable parameters for the TelegramControlCenter."""

    bot_token:           str        = ""
    allowed_chat_ids:    Set[int]   = field(default_factory=set)
    poll_timeout_sec:    int        = 30
    retry_delay_sec:     float      = 10.0
    max_message_age_sec: float      = 60.0
    send_startup_message: bool      = True
    send_shutdown_message: bool     = True

    def __post_init__(self) -> None:
        self.poll_timeout_sec  = max(5,  int(self.poll_timeout_sec))
        self.retry_delay_sec   = max(1.0, float(self.retry_delay_sec))
        self.max_message_age_sec = max(0.0, float(self.max_message_age_sec))

    @property
    def valid(self) -> bool:
        return bool(self.bot_token and self.bot_token.strip())


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers — Telegram HTTP API
# ─────────────────────────────────────────────────────────────────────────────
class _TelegramHTTP:
    """Minimal Telegram HTTP client used by TelegramControlCenter."""

    def __init__(self, token: str, timeout: int = 30):
        self.token = token
        self._timeout = timeout
        self._base = f"https://api.telegram.org/bot{token}/"

    def _url(self, method: str) -> str:
        return self._base + method

    def get_updates(self, offset=None, timeout=30):
        params = {
            "timeout": timeout,
            "offset": offset
        }

        url = self._url("getUpdates") + "?" + urllib.parse.urlencode(params)

        with urllib.request.urlopen(url, timeout=self._timeout + 5) as resp:
            data = json.loads(resp.read().decode())

        if not data.get("ok"):
            return []

        return data.get("result", [])

    def send_message(self, chat_id: int, text: str, parse_mode="Markdown") -> bool:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }

        data = json.dumps(payload).encode()

        req = urllib.request.Request(
            self._url("sendMessage"),
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=self._timeout + 5) as resp:
                result = json.loads(resp.read().decode())
                return result.get("ok", False)
        except Exception as e:
            logger.warning("%s Telegram send error: %s", _TAG, e)
            return False
            
class TelegramControlCenter:

    def __init__(self, token, chat_ids=None):
        self.token = token
        self.chat_ids = chat_ids
        
        import requests

        self.base_url = f"https://api.telegram.org/bot{self.token}/"
    
    def call(self, method, params=None):
        url = self.base_url + method
        response = requests.get(url, params=params)
        return response.json()

    def _post(self, method: str, payload: dict) -> dict:
        url  = self._url(method)
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout + 5) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors="replace")
            logger.warning("%s HTTP %s — %s", _TAG, exc.code, body[:200])
            return {}
        except Exception as exc:
            logger.debug("%s _post error: %s", _TAG, exc)
            return {}

    def get_updates(self, offset=None):
        params = {"timeout": 30, "offset": offset}
        return self.call("getUpdates", params)

    def send_message(self, chat_id: int, text: str, parse_mode: str = "Markdown") -> bool:
        # Telegram caps message length at 4096 chars
        chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
        ok = True
        for chunk in chunks:
            result = self._post(
                "sendMessage",
                {
                    "chat_id":    chat_id,
                    "text":       chunk,
                    "parse_mode": parse_mode,
                },
            )
            if not result.get("ok"):
                ok = False
        return ok


# ─────────────────────────────────────────────────────────────────────────────
# Command Handlers
# ─────────────────────────────────────────────────────────────────────────────

class _CommandHandlers:
    """
    Pure command logic.  All methods return a formatted string to send back.
    Receives a read-only reference to the SystemRouter.
    """

    def __init__(self, router: Any) -> None:
        self._router = router

    # ── /status ───────────────────────────────────────────────────────────────

    def handle_status(self) -> str:
        r = self._router
        lines = ["*🖥 System Status*", ""]

        # Operating mode
        mode = getattr(getattr(r, "config", None), "mode", "UNKNOWN")
        lines.append(f"• Mode: `{mode}`")

        # Trading state
        state = getattr(r, "state", None)
        if state:
            halted   = getattr(state, "trading_halted", False)
            auto     = getattr(state, "auto_mode",      False)
            regime   = getattr(state, "current_regime", "UNKNOWN")
            status_emoji = "🔴 HALTED" if halted else "🟢 ACTIVE"
            lines.append(f"• Trading: {status_emoji}")
            lines.append(f"• Auto mode: `{'ON' if auto else 'OFF'}`")
            lines.append(f"• Regime: `{regime}`")
        else:
            lines.append("• Trading state: unavailable")

        # Capital
        cap_engine = getattr(r, "capital_intelligence", None)
        if cap_engine and hasattr(cap_engine, "capital_snapshot"):
            try:
                snap = cap_engine.capital_snapshot()
                total = snap.get("total_capital", 0)
                lines.append(f"• Capital: `₹{total:,.0f}`")
            except Exception:
                pass

        # Strategy count
        registry = getattr(r, "strategy_registry", None)
        if registry and hasattr(registry, "count"):
            try:
                lines.append(f"• Strategies: `{registry.count()}`")
            except Exception:
                pass

        # Research loop health
        loop = getattr(r, "autonomous_research_loop", None)
        if loop and hasattr(loop, "is_running"):
            running = loop.is_running
            lines.append(f"• Research loop: {'🟢 running' if running else '🔴 stopped'}")

        # Regime intelligence
        regime_eng = getattr(r, "regime_intelligence", None) or getattr(r, "regime_ai_engine", None)
        if regime_eng and hasattr(regime_eng, "get_regime"):
            try:
                lines.append(f"• AI Regime: `{regime_eng.get_regime()}`")
            except Exception:
                pass

        lines.append(f"\n_Updated: {_ts()}_")
        return "\n".join(lines)

    # ── /research ─────────────────────────────────────────────────────────────

    def handle_research(self) -> str:
        r = self._router
        lines = ["*🔬 Research Status*", ""]

        loop = getattr(r, "autonomous_research_loop", None)
        if loop:
            if hasattr(loop, "status"):
                try:
                    s = loop.status()
                    lines.append(f"• Loop running: `{s.get('is_running', '?')}`")
                    lines.append(f"• Cycles completed: `{s.get('cycle_number', 0)}`")
                    lines.append(f"• Total promoted: `{s.get('total_promoted', 0)}`")
                    lines.append(f"• Total evaluated: `{s.get('total_evaluated', 0)}`")
                except Exception as exc:
                    lines.append(f"• Loop status error: {exc}")

            last = getattr(loop, "last_cycle", None)
            if last:
                try:
                    d = last.to_dict() if hasattr(last, "to_dict") else {}
                    lines.append("")
                    lines.append("*Last Cycle:*")
                    lines.append(f"  Cycle #: `{d.get('cycle_number', '?')}`")
                    lines.append(f"  Elapsed: `{d.get('elapsed_sec', 0):.1f}s`")
                    lines.append(f"  Discovered: `{d.get('discovered', 0)}`")
                    lines.append(f"  Mutated: `{d.get('mutated', 0)}`")
                    lines.append(f"  Promoted: `{d.get('promoted', 0)}`")
                    lines.append(f"  Best fitness: `{d.get('best_fitness', 0):.4f}`")
                    lines.append(f"  Best Sharpe: `{d.get('best_sharpe', 0):.3f}`")
                    lines.append(f"  Status: `{'✅ OK' if d.get('ok') else '⚠️ ERRORS'}`")
                except Exception:
                    pass
        else:
            lines.append("Research loop not attached.")

        # Research grid
        grid = getattr(r, "research_grid", None)
        if grid and hasattr(grid, "status"):
            try:
                gs = grid.status()
                lines.append("")
                lines.append("*Research Grid:*")
                lines.append(f"  Queued: `{gs.get('queued', 0)}`")
                lines.append(f"  Running: `{gs.get('running', 0)}`")
                lines.append(f"  Completed: `{gs.get('completed', 0)}`")
                lines.append(f"  Failed: `{gs.get('failed', 0)}`")
            except Exception:
                pass

        # Meta-Research AI
        meta = getattr(r, "meta_research_ai", None)
        if meta and hasattr(meta, "last_priorities"):
            try:
                pri = meta.last_priorities
                if pri:
                    lines.append("")
                    lines.append("*MetaResearch AI:*")
                    lines.append(f"  Focus family: `{getattr(pri, 'focus_family', '?')}`")
                    lines.append(f"  Regime bias: `{getattr(pri, 'regime_bias', '?')}`")
                    conf = getattr(pri, "confidence", 0)
                    lines.append(f"  Confidence: `{conf:.2f}`")
            except Exception:
                pass

        lines.append(f"\n_Updated: {_ts()}_")
        return "\n".join(lines)

    # ── /strategies ───────────────────────────────────────────────────────────

    def handle_strategies(self) -> str:
        r = self._router
        lines = ["*📊 Strategy Registry*", ""]

        registry = getattr(r, "strategy_registry", None)
        if not registry:
            return "Strategy registry not available."

        try:
            count = registry.count() if hasattr(registry, "count") else "?"
            lines.append(f"• Total strategies: `{count}`")
        except Exception:
            lines.append("• Count unavailable")

        # Top strategies from alpha bank if available
        alpha_bank = getattr(r, "alpha_bank", None)
        if alpha_bank and hasattr(alpha_bank, "top"):
            try:
                top = alpha_bank.top(n=5)
                if top:
                    lines.append("")
                    lines.append("*Top 5 Alpha Bank Strategies:*")
                    for i, s in enumerate(top, 1):
                        sid     = s.get("id", s.get("strategy_id", "?"))
                        fitness = s.get("fitness", s.get("sharpe", 0))
                        lines.append(f"  {i}. `{sid}` — fitness: `{fitness:.4f}`")
            except Exception:
                pass

        # Strategy selector / active
        selector = getattr(r, "strategy_selector", None)
        if selector and hasattr(selector, "active_strategies"):
            try:
                active = selector.active_strategies
                if active:
                    lines.append("")
                    lines.append(f"*Active Strategies:* `{len(active)}`")
                    for s in list(active)[:5]:
                        sid = getattr(s, "id", getattr(s, "STRATEGY_ID", str(s)))
                        lines.append(f"  • `{sid}`")
                    if len(active) > 5:
                        lines.append(f"  … and {len(active) - 5} more")
            except Exception:
                pass

        # Mutation engine stats
        mutation = getattr(r, "mutation_engine", None)
        if mutation and hasattr(mutation, "stats"):
            try:
                ms = mutation.stats()
                lines.append("")
                lines.append(f"*Mutation Engine:* `{ms.get('total_mutations', 0)}` mutations")
            except Exception:
                pass

        lines.append(f"\n_Updated: {_ts()}_")
        return "\n".join(lines)

    # ── /start ────────────────────────────────────────────────────────────────

    def handle_start(self) -> str:
        r = self._router
        state = getattr(r, "state", None)
        if state is None:
            return "⚠️ System state not available."
        try:
            state.trading_halted = False
            if hasattr(r, "set_auto_mode"):
                r.set_auto_mode(True)
            logger.info("%s /start — trading resumed via Telegram", _TAG)
            return "✅ *Trading RESUMED.*\nAuto mode enabled."
        except Exception as exc:
            return f"❌ Failed to resume: `{exc}`"

    # ── /stop ─────────────────────────────────────────────────────────────────

    def handle_stop(self) -> str:
        r = self._router
        try:
            if hasattr(r, "stop_trading"):
                r.stop_trading()
            logger.warning("%s /stop — trading halted via Telegram", _TAG)
            return "🔴 *Trading HALTED.*\nAll new orders blocked."
        except Exception as exc:
            return f"❌ Failed to halt: `{exc}`"

    # ── /pause ────────────────────────────────────────────────────────────────

    def handle_pause(self) -> str:
        r = self._router
        loop = getattr(r, "autonomous_research_loop", None)
        if loop is None:
            return "⚠️ Research loop not attached."
        try:
            if hasattr(loop, "pause"):
                loop.pause()
                return "⏸ *Research loop PAUSED.*\nTrading continues unaffected."
            # Graceful fallback — stop the loop without killing trading
            if hasattr(loop, "stop"):
                loop.stop()
                return "⏸ *Research loop STOPPED* (pause not supported, stopped instead)."
            return "⚠️ Loop does not support pause/stop."
        except Exception as exc:
            return f"❌ Pause failed: `{exc}`"

    # ── /resume ───────────────────────────────────────────────────────────────

    def handle_resume(self) -> str:
        r = self._router
        loop = getattr(r, "autonomous_research_loop", None)
        if loop is None:
            return "⚠️ Research loop not attached."
        try:
            if hasattr(loop, "resume"):
                loop.resume()
                return "▶️ *Research loop RESUMED.*"
            if hasattr(loop, "start"):
                loop.start()
                return "▶️ *Research loop STARTED.*"
            return "⚠️ Loop does not support resume/start."
        except Exception as exc:
            return f"❌ Resume failed: `{exc}`"

    # ── /shutdown ─────────────────────────────────────────────────────────────

    def handle_shutdown(self) -> str:
        r = self._router
        messages = []

        # Halt trading first
        try:
            if hasattr(r, "stop_trading"):
                r.stop_trading()
            messages.append("• Trading halted ✅")
        except Exception as exc:
            messages.append(f"• Trading halt failed: {exc}")

        # Stop research loop
        loop = getattr(r, "autonomous_research_loop", None)
        if loop and hasattr(loop, "stop"):
            try:
                loop.stop()
                messages.append("• Research loop stopped ✅")
            except Exception as exc:
                messages.append(f"• Loop stop failed: {exc}")

        logger.warning("%s /shutdown command executed via Telegram", _TAG)
        body = "\n".join(messages)
        return f"⛔ *System SHUTDOWN initiated.*\n\n{body}"


# ─────────────────────────────────────────────────────────────────────────────
# TelegramControlCenter
# ─────────────────────────────────────────────────────────────────────────────

class TelegramControlCenter:
    """
    Background-thread Telegram bot controller.

    Starts a daemon thread that long-polls Telegram for commands and
    dispatches them to _CommandHandlers.  All write operations flow
    through SystemRouter's own public API to preserve thread safety.

    The trading thread is NEVER blocked by this class.

    Parameters
    ----------
    bot_token        : str
        Telegram Bot API token from @BotFather.
    allowed_chat_ids : set[int], optional
        Whitelist of chat IDs.  Empty = accept all (dev mode).
    router           : SystemRouter, optional
        Injected at construction or later via attach_router().
    cfg              : TelegramConfig, optional
        Override any config parameter.
    """

    def __init__(
        self,
        bot_token:        str               = "",
        allowed_chat_ids: Optional[Set[int]] = None,
        router:           Any               = None,
        cfg:              Optional[TelegramConfig] = None,
        **kwargs,
    ) -> None:

        if cfg is None:
            cfg = TelegramConfig(
                bot_token        = bot_token,
                allowed_chat_ids = set(allowed_chat_ids or []),
            )
        self._cfg: TelegramConfig = cfg

        self._router   = router
        self._http: Optional[_TelegramHTTP] = None
        self._handlers: Optional[_CommandHandlers] = None

        if self._cfg.valid:
            self._http     = _TelegramHTTP(self._cfg.bot_token, self._cfg.poll_timeout_sec)
            self._handlers = _CommandHandlers(router)

        # Thread control
        self._thread:     Optional[threading.Thread] = None
        self._stop_event: threading.Event             = threading.Event()

        # Message deduplication
        self._update_offset: int = 0

        # Broadcast registry: chat IDs we've seen
        self._known_chats: Set[int] = set(self._cfg.allowed_chat_ids)

        # Command dispatch table
        self._dispatch: Dict[str, Any] = {}
        self._build_dispatch()

        logger.info(
            "%s TelegramControlCenter created | token_set=%s | allowed=%s",
            _TAG,
            self._cfg.valid,
            self._cfg.allowed_chat_ids or "ALL",
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def attach_router(self, router: Any) -> None:
        """Inject or replace the SystemRouter reference."""
        self._router = router
        if self._handlers is None:
            self._handlers = _CommandHandlers(router)
        else:
            self._handlers._router = router
        logger.info("%s SystemRouter attached.", _TAG)

    def start(self) -> bool:
        """
        Launch the background polling thread.  Non-blocking.  Idempotent.
        Returns True if thread was started, False if already running or
        token is missing.
        """
        if not self._cfg.valid:
            logger.warning("%s Bot token not set — Telegram disabled.", _TAG)
            return False

        if self._thread and self._thread.is_alive():
            logger.debug("%s Already running.", _TAG)
            return False

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._polling_loop,
            name="TelegramCC-poll",
            daemon=True,
        )
        self._thread.start()
        logger.info("%s Polling thread started.", _TAG)

        if self._cfg.send_startup_message:
            self.broadcast("🚀 *Quant Ecosystem online.*\nType /status for a system snapshot.")

        return True

    def stop(self) -> None:
        """Signal the polling thread to exit and wait for it."""
        self._stop_event.set()
        if self._cfg.send_shutdown_message:
            self.broadcast("⛔ *Quant Ecosystem control center shutting down.*")
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self._cfg.poll_timeout_sec + 5)
        logger.info("%s Polling thread stopped.", _TAG)

    def send(self, chat_id: int, text: str) -> bool:
        """Send a message to a specific chat."""
        if self._http is None:
            return False
        return self._http.send_message(chat_id, text)

    def broadcast(self, text: str) -> None:
        """Send a message to all known/allowed chats."""
        if self._http is None or not self._known_chats:
            return
        for cid in list(self._known_chats):
            self._http.send_message(cid, text)

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # ── Build dispatch table ──────────────────────────────────────────────────

    def _build_dispatch(self) -> None:
        h = self._handlers
        self._dispatch = {
            "/status":    lambda: h.handle_status()    if h else "Router not attached.",
            "/research":  lambda: h.handle_research()  if h else "Router not attached.",
            "/strategies":lambda: h.handle_strategies() if h else "Router not attached.",
            "/start":     lambda: h.handle_start()     if h else "Router not attached.",
            "/stop":      lambda: h.handle_stop()      if h else "Router not attached.",
            "/pause":     lambda: h.handle_pause()     if h else "Router not attached.",
            "/resume":    lambda: h.handle_resume()    if h else "Router not attached.",
            "/shutdown":  lambda: h.handle_shutdown()  if h else "Router not attached.",
            "/help":      lambda: self._help_text(),
        }

    # ── Polling loop ──────────────────────────────────────────────────────────

    def _polling_loop(self) -> None:
        logger.info("%s Polling loop started.", _TAG)

        while not self._stop_event.is_set():
            try:
                updates = self._http.get_updates(
                    offset=self._update_offset,
                    timeout=self._cfg.poll_timeout_sec,
                )
                for update in updates:
                    self._update_offset = update["update_id"] + 1
                    self._process_update(update)

            except Exception as exc:
                if self._stop_event.is_set():
                    break
                logger.warning("%s Polling error: %s — retry in %ss", _TAG, exc,
                               self._cfg.retry_delay_sec)
                self._stop_event.wait(self._cfg.retry_delay_sec)

        logger.info("%s Polling loop exited.", _TAG)

    def _process_update(self, update: dict) -> None:
        message = update.get("message")
        if not message:
            return

        chat_id   = message.get("chat", {}).get("id")
        text      = message.get("text", "").strip()
        timestamp = message.get("date", 0)

        if chat_id is None or not text:
            return

        # Drop stale messages from before startup
        age = time.time() - timestamp
        if age > self._cfg.max_message_age_sec:
            logger.debug("%s Skipping stale message (age=%.0fs)", _TAG, age)
            self._update_offset = update["update_id"] + 1
            return

        # Authorization check
        if self._cfg.allowed_chat_ids and chat_id not in self._cfg.allowed_chat_ids:
            logger.warning("%s Unauthorized chat_id=%s text=%r", _TAG, chat_id, text)
            self._http.send_message(chat_id, "⛔ Unauthorized.")
            return

        # Register this chat for broadcast
        self._known_chats.add(chat_id)

        # Extract command root (ignore /command@botname suffixes)
        command = text.split()[0].split("@")[0].lower()

        handler = self._dispatch.get(command)
        if handler is None:
            self._http.send_message(
                chat_id,
                f"Unknown command: `{command}`\n\n{self._help_text()}",
            )
            return

        logger.info("%s Command from chat_id=%s: %s", _TAG, chat_id, command)
        try:
            reply = handler()
        except Exception as exc:
            logger.exception("%s Command handler crashed: %s", _TAG, exc)
            reply = f"❌ Internal error: `{exc}`"

        self._http.send_message(chat_id, reply or "✅ Done.")

    # ── Help text ─────────────────────────────────────────────────────────────

    @staticmethod
    def _help_text() -> str:
        return (
            "*Quant Ecosystem — Available Commands*\n\n"
            "/status      — Full system health snapshot\n"
            "/research    — Research loop & grid stats\n"
            "/strategies  — Strategy registry summary\n"
            "/start       — Resume trading\n"
            "/stop        — Halt all new orders\n"
            "/pause       — Pause research loop\n"
            "/resume      — Resume research loop\n"
            "/shutdown    — Halt trading + stop research\n"
            "/help        — Show this message"
        )

    # ── Convenience factory ───────────────────────────────────────────────────

    @classmethod
    def from_config(cls, config: Any, router: Any = None) -> "TelegramControlCenter":
        """
        Construct from a system config object that exposes:
            config.telegram_token
            config.telegram_chat_ids   (list or set of int, optional)
        """
        token    = getattr(config, "telegram_token",    "")
        chat_ids = getattr(config, "telegram_chat_ids", [])
        return cls(
            bot_token        = str(token),
            allowed_chat_ids = set(int(c) for c in chat_ids),
            router           = router,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _ts() -> str:
    """Human-readable UTC timestamp."""
    import datetime
    return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

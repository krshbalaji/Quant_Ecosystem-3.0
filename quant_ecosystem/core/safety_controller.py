"""
quant_ecosystem/core/safety_controller.py
==========================================
Safety Controller — Kill Switch, Loss Guard & Emergency Shutdown
Quant Ecosystem 3.0

Responsibilities
----------------
1. Kill Switch         — hard halt of all trading activity (manual or automatic)
2. Daily Loss Guard    — auto-halt when intraday drawdown exceeds threshold
3. Broker Disconnect   — halt + alert when broker connection is lost
4. Emergency Shutdown  — ordered teardown of all engine layers
5. State persistence   — writes halt state to disk so restarts honour the flag

Usage
-----
    from quant_ecosystem.core.safety_controller import SafetyController

    safety = SafetyController(config=config, mode="PAPER")
    safety.register_router(router)          # wire the engine graph

    # Inside risk loop:
    safety.update_pnl(current_pnl=-1500)   # auto-halts if threshold hit

    # Manual kill:
    safety.kill_switch("Operator override")
"""

from __future__ import annotations

import json
import os
import signal
import sys
import threading
import time
import traceback
from datetime import datetime, date
from typing import Any, Callable, Dict, List, Optional


# ──────────────────────────────────────────────────────────────────────────────
# Constants / defaults
# ──────────────────────────────────────────────────────────────────────────────

DEFAULT_DAILY_LOSS_LIMIT   = -5_000.0    # USD — override via config
DEFAULT_MAX_DRAWDOWN_PCT   = -0.05       # 5 %  of starting equity
HALT_STATE_FILE            = "/tmp/quant_ecosystem_halt.json"
BROKER_POLL_INTERVAL_SEC   = 30          # how often to probe broker in LIVE mode
_LOCK                      = threading.Lock()


# ──────────────────────────────────────────────────────────────────────────────
# Event record
# ──────────────────────────────────────────────────────────────────────────────

class SafetyEvent:
    """Immutable record of a safety trigger."""

    def __init__(self, reason: str, level: str, source: str):
        self.reason    = reason
        self.level     = level      # "KILL" | "HALT" | "WARN"
        self.source    = source
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "level":     self.level,
            "source":    self.source,
            "reason":    self.reason,
        }

    def __str__(self) -> str:
        return f"[{self.level}] {self.timestamp} | {self.source} | {self.reason}"


# ──────────────────────────────────────────────────────────────────────────────
# SafetyController
# ──────────────────────────────────────────────────────────────────────────────

class SafetyController:
    """
    Central safety layer for Quant Ecosystem 3.0.

    Parameters
    ----------
    config : dict, optional
        System config. Recognised keys:
            DAILY_LOSS_LIMIT   float  — absolute USD loss that triggers halt
            MAX_DRAWDOWN_PCT   float  — fractional drawdown (negative) for halt
            STARTING_EQUITY    float  — baseline equity for drawdown calculation
            PAPER              bool   — True forces PAPER mode
            mode               str    — "PAPER" | "LIVE"
    mode : str
        "PAPER" (default) or "LIVE".
    """

    def __init__(self, config: Optional[dict] = None, mode: str = "PAPER"):
        self.config  = config or {}
        self.mode    = self.config.get("mode", mode).upper()

        # ── thresholds ───────────────────────────────────────────────
        self._daily_loss_limit = float(
            self.config.get("DAILY_LOSS_LIMIT", DEFAULT_DAILY_LOSS_LIMIT)
        )
        self._max_drawdown_pct = float(
            self.config.get("MAX_DRAWDOWN_PCT", DEFAULT_MAX_DRAWDOWN_PCT)
        )
        self._starting_equity = float(self.config.get("STARTING_EQUITY", 100_000.0))

        # ── runtime state ────────────────────────────────────────────
        self._halted: bool = False
        self._kill_reason: Optional[str] = None
        self._daily_pnl: float = 0.0
        self._peak_equity: float = self._starting_equity
        self._current_equity: float = self._starting_equity
        self._last_reset_date: date = date.today()
        self._event_log: List[SafetyEvent] = []

        # ── wired components ─────────────────────────────────────────
        self._router = None
        self._telegram = None
        self._broker = None
        self._shutdown_hooks: List[Callable] = []

        # ── broker watchdog thread (LIVE only) ───────────────────────
        self._broker_watchdog_thread: Optional[threading.Thread] = None
        self._broker_watchdog_active: bool = False

        # ── restore persisted halt if it exists ──────────────────────
        self._restore_halt_state()

        print(
            f"[SafetyController] Initialized | mode={self.mode} | "
            f"daily_loss_limit={self._daily_loss_limit:,.0f} | "
            f"max_drawdown={self._max_drawdown_pct:.1%}"
        )

    # ──────────────────────────────────────────────────────────────────
    # Wiring
    # ──────────────────────────────────────────────────────────────────

    def register_router(self, router) -> None:
        """Wire the engine graph so SafetyController can reach all layers."""
        self._router = router
        self._telegram = getattr(router, "telegram", None)
        self._broker   = (
            getattr(router, "broker", None)
            or getattr(router, "execution_router", None)
        )
        if self.mode == "LIVE" and self._broker is not None:
            self._start_broker_watchdog()

    def register_shutdown_hook(self, fn: Callable) -> None:
        """
        Register a zero-argument callable that will be invoked during
        emergency shutdown (e.g. lambda: engine.stop()).
        """
        self._shutdown_hooks.append(fn)

    # ──────────────────────────────────────────────────────────────────
    # Kill Switch
    # ──────────────────────────────────────────────────────────────────

    def kill_switch(self, reason: str = "Manual kill switch activated") -> None:
        """
        Immediate hard stop.  Halts all trading, notifies Telegram,
        persists halt state, and invokes registered shutdown hooks.

        Safe to call multiple times — idempotent.
        """
        with _LOCK:
            if self._halted and self._kill_reason:
                print(f"[SafetyController] Already halted: {self._kill_reason}")
                return

            self._halted      = True
            self._kill_reason = reason

        event = SafetyEvent(reason=reason, level="KILL", source="kill_switch")
        self._log_event(event)
        self._persist_halt_state()
        self._notify(f"🛑 KILL SWITCH: {reason}")
        self._invoke_shutdown_hooks()

        print(f"[SafetyController] *** KILL SWITCH *** {reason}")

    # ──────────────────────────────────────────────────────────────────
    # Daily Loss Guard
    # ──────────────────────────────────────────────────────────────────

    def update_pnl(self, current_pnl: float, current_equity: Optional[float] = None) -> bool:
        """
        Report current intraday P&L and optionally current equity.

        Returns True if trading may continue, False if halted.
        Call this inside your main risk loop (e.g. every 60 seconds).
        """
        self._reset_daily_if_needed()
        self._daily_pnl = current_pnl

        if current_equity is not None:
            self._current_equity = current_equity
            self._peak_equity    = max(self._peak_equity, current_equity)

        # Absolute daily loss check
        if self._daily_pnl <= self._daily_loss_limit:
            self.kill_switch(
                f"Daily loss limit hit: P&L={self._daily_pnl:,.2f} "
                f"<= limit={self._daily_loss_limit:,.2f}"
            )
            return False

        # Drawdown % check (requires equity tracking)
        if self._peak_equity > 0:
            drawdown_pct = (self._current_equity - self._peak_equity) / self._peak_equity
            if drawdown_pct <= self._max_drawdown_pct:
                self.kill_switch(
                    f"Max drawdown hit: {drawdown_pct:.2%} "
                    f"<= threshold={self._max_drawdown_pct:.2%}"
                )
                return False

        return not self._halted

    # ──────────────────────────────────────────────────────────────────
    # Broker Disconnect Guard
    # ──────────────────────────────────────────────────────────────────

    def handle_broker_disconnect(self, reason: str = "Broker disconnected") -> None:
        """
        Called when broker connectivity is lost.
        In LIVE mode: triggers kill switch.
        In PAPER mode: logs warning only.
        """
        event = SafetyEvent(reason=reason, level="HALT", source="broker_guard")
        self._log_event(event)

        if self.mode == "LIVE":
            self.kill_switch(f"BROKER DISCONNECT — {reason}")
        else:
            self._notify(f"⚠️  PAPER mode — broker disconnect simulated: {reason}")
            print(f"[SafetyController] PAPER broker disconnect (non-fatal): {reason}")

    # ──────────────────────────────────────────────────────────────────
    # Emergency Shutdown
    # ──────────────────────────────────────────────────────────────────

    def emergency_shutdown(self, reason: str = "Emergency shutdown") -> None:
        """
        Ordered teardown:
        1. Activate kill switch
        2. Stop market data feed
        3. Stop strategy engines
        4. Flush order queue
        5. Notify Telegram
        6. Invoke all registered shutdown hooks
        7. Exit process
        """
        print(f"\n[SafetyController] ════ EMERGENCY SHUTDOWN ════")
        print(f"[SafetyController] Reason: {reason}")

        self.kill_switch(reason)

        # Ordered teardown via router
        if self._router is not None:
            self._safe_stop(self._router, "market_data",        "MarketDataEngine")
            self._safe_stop(self._router, "live_strategy",      "LiveStrategyEngine")
            self._safe_stop(self._router, "execution_router",   "ExecutionRouter")
            self._safe_stop(self._router, "pulse",              "PulseEngine")
            self._safe_stop(self._router, "event_orchestrator", "EventOrchestrator")

        self._notify(f"🚨 EMERGENCY SHUTDOWN COMPLETE: {reason}")
        print("[SafetyController] ════ SHUTDOWN COMPLETE ════\n")

        # Exit the process — use os._exit in threaded context to avoid hangs
        try:
            os._exit(1)
        except Exception:
            sys.exit(1)

    # ──────────────────────────────────────────────────────────────────
    # State queries
    # ──────────────────────────────────────────────────────────────────

    @property
    def is_halted(self) -> bool:
        return self._halted

    @property
    def halt_reason(self) -> Optional[str]:
        return self._kill_reason

    def status(self) -> Dict[str, Any]:
        return {
            "halted":            self._halted,
            "kill_reason":       self._kill_reason,
            "mode":              self.mode,
            "daily_pnl":         self._daily_pnl,
            "daily_loss_limit":  self._daily_loss_limit,
            "peak_equity":       self._peak_equity,
            "current_equity":    self._current_equity,
            "max_drawdown_pct":  self._max_drawdown_pct,
            "event_count":       len(self._event_log),
            "last_event":        str(self._event_log[-1]) if self._event_log else None,
        }

    def get_event_log(self) -> List[dict]:
        return [e.to_dict() for e in self._event_log]

    # ──────────────────────────────────────────────────────────────────
    # Reset (new trading day / operator clear)
    # ──────────────────────────────────────────────────────────────────

    def reset_halt(self, operator_code: str = "") -> bool:
        """
        Clear halt state.  Requires operator_code matching config key
        RESET_CODE in LIVE mode; unconditional in PAPER mode.
        """
        expected = self.config.get("RESET_CODE", "")
        if self.mode == "LIVE" and operator_code != expected:
            print("[SafetyController] Reset DENIED — incorrect operator code.")
            return False

        with _LOCK:
            self._halted      = False
            self._kill_reason = None

        self._clear_halt_state()
        event = SafetyEvent("Halt cleared by operator", "WARN", "reset_halt")
        self._log_event(event)
        self._notify("✅ Safety halt cleared by operator.")
        print("[SafetyController] Halt state CLEARED.")
        return True

    # ──────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────

    def _reset_daily_if_needed(self) -> None:
        today = date.today()
        if today != self._last_reset_date:
            self._daily_pnl       = 0.0
            self._last_reset_date = today
            print(f"[SafetyController] Daily P&L counter reset for {today}.")

    def _notify(self, message: str) -> None:
        """Send message via Telegram if available, else print."""
        if self._telegram is not None:
            try:
                send_fn = getattr(self._telegram, "send", None) or getattr(
                    self._telegram, "alert", None
                )
                if callable(send_fn):
                    send_fn(message)
                    return
            except Exception as exc:
                print(f"[SafetyController] Telegram notify failed: {exc}")
        print(f"[SafetyController] NOTIFY: {message}")

    def _log_event(self, event: SafetyEvent) -> None:
        self._event_log.append(event)
        print(f"[SafetyController] Event: {event}")

    def _invoke_shutdown_hooks(self) -> None:
        for hook in self._shutdown_hooks:
            try:
                hook()
            except Exception as exc:
                print(f"[SafetyController] Shutdown hook error: {exc}")

    def _safe_stop(self, router, attr: str, label: str) -> None:
        obj = getattr(router, attr, None)
        if obj is None:
            return
        for method_name in ("stop", "shutdown", "close", "disconnect"):
            method = getattr(obj, method_name, None)
            if callable(method):
                try:
                    method()
                    print(f"[SafetyController] Stopped {label}.{method_name}()")
                    return
                except Exception as exc:
                    print(f"[SafetyController] {label}.{method_name}() error: {exc}")
                    return

    # ── Broker watchdog ───────────────────────────────────────────────

    def _start_broker_watchdog(self) -> None:
        self._broker_watchdog_active = True
        self._broker_watchdog_thread = threading.Thread(
            target=self._broker_watchdog_loop,
            name="BrokerWatchdog",
            daemon=True,
        )
        self._broker_watchdog_thread.start()
        print("[SafetyController] Broker watchdog started.")

    def _broker_watchdog_loop(self) -> None:
        while self._broker_watchdog_active and not self._halted:
            time.sleep(BROKER_POLL_INTERVAL_SEC)
            if self._halted:
                break
            try:
                connected = self._probe_broker_connection()
                if not connected:
                    self.handle_broker_disconnect("Watchdog: broker ping failed")
            except Exception as exc:
                print(f"[SafetyController] Watchdog error: {exc}")

    def _probe_broker_connection(self) -> bool:
        if self._broker is None:
            return False
        for method_name in ("is_connected", "ping", "status"):
            probe = getattr(self._broker, method_name, None)
            if callable(probe):
                try:
                    val = probe()
                    return bool(val)
                except Exception:
                    return False
        return True  # assume OK if no probe method

    # ── Halt state persistence ────────────────────────────────────────

    def _persist_halt_state(self) -> None:
        try:
            payload = {
                "halted":      True,
                "reason":      self._kill_reason,
                "timestamp":   datetime.utcnow().isoformat(),
                "mode":        self.mode,
            }
            with open(HALT_STATE_FILE, "w") as fh:
                json.dump(payload, fh, indent=2)
            print(f"[SafetyController] Halt state written to {HALT_STATE_FILE}")
        except Exception as exc:
            print(f"[SafetyController] Could not persist halt state: {exc}")

    def _restore_halt_state(self) -> None:
        if not os.path.exists(HALT_STATE_FILE):
            return
        try:
            with open(HALT_STATE_FILE) as fh:
                payload = json.load(fh)
            if payload.get("halted"):
                self._halted      = True
                self._kill_reason = payload.get("reason", "Restored from disk")
                print(
                    f"[SafetyController] ⚠️  RESTORED HALT STATE from disk: "
                    f"{self._kill_reason}"
                )
        except Exception as exc:
            print(f"[SafetyController] Could not restore halt state: {exc}")

    def _clear_halt_state(self) -> None:
        try:
            if os.path.exists(HALT_STATE_FILE):
                os.remove(HALT_STATE_FILE)
        except Exception as exc:
            print(f"[SafetyController] Could not clear halt state file: {exc}")

"""
quant_ecosystem/core/system_integrity_check.py
===============================================
System Integrity & Self-Healing Diagnostic Engine
Quant Ecosystem 3.0

Responsibilities
----------------
- Detect missing modules and boot layers
- Detect broken / unimportable engine classes
- Detect recursion errors in engine constructors
- Detect Telegram connectivity issues
- Detect broker / market-data feed health
- Emit a structured DiagnosticReport without crashing the boot process

Usage (inside boot sequence)
-----------------------------
    from quant_ecosystem.core.system_integrity_check import SystemIntegrityCheck

    diagnostics = SystemIntegrityCheck(mode="PAPER")
    report = diagnostics.run_full_diagnostic(router)

    if report.system_status == "CRITICAL":
        shutdown()
"""

from __future__ import annotations

import importlib
import sys
import traceback
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ──────────────────────────────────────────────────────────────────────────────
# Report dataclass
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class DiagnosticReport:
    """
    Structured output of a full diagnostic pass.

    system_status : "HEALTHY" | "DEGRADED" | "CRITICAL"
    missing_modules : modules that could not be imported
    broken_engines  : engines that raised during construction or import
    warnings        : non-fatal advisory messages
    details         : arbitrary per-check result dicts for deeper inspection
    """
    system_status: str = "HEALTHY"          # HEALTHY | DEGRADED | CRITICAL
    missing_modules: List[str] = field(default_factory=list)
    broken_engines: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Severity helpers
    # ------------------------------------------------------------------

    def _escalate(self, level: str) -> None:
        """Raise system_status only — never downgrade."""
        order = {"HEALTHY": 0, "DEGRADED": 1, "CRITICAL": 2}
        if order.get(level, 0) > order.get(self.system_status, 0):
            self.system_status = level

    def add_critical(self, msg: str) -> None:
        self.warnings.append(f"[CRITICAL] {msg}")
        self._escalate("CRITICAL")

    def add_degraded(self, msg: str) -> None:
        self.warnings.append(f"[DEGRADED] {msg}")
        self._escalate("DEGRADED")

    def add_warning(self, msg: str) -> None:
        self.warnings.append(f"[WARNING]  {msg}")
        # warnings alone do not change status

    def to_dict(self) -> dict:
        return {
            "system_status":   self.system_status,
            "missing_modules": self.missing_modules,
            "broken_engines":  self.broken_engines,
            "warnings":        self.warnings,
            "details":         self.details,
        }

    def pretty(self) -> str:
        lines = [
            "╔══════════════════════════════════════════════════╗",
            f"║  SYSTEM INTEGRITY REPORT — {self.system_status:<20} ║",
            "╚══════════════════════════════════════════════════╝",
        ]
        if self.missing_modules:
            lines.append("  Missing modules:")
            lines += [f"    • {m}" for m in self.missing_modules]
        if self.broken_engines:
            lines.append("  Broken engines:")
            lines += [f"    • {e}" for e in self.broken_engines]
        if self.warnings:
            lines.append("  Warnings / Notices:")
            lines += [f"    {w}" for w in self.warnings]
        if not (self.missing_modules or self.broken_engines or self.warnings):
            lines.append("  ✓ All checks passed.")
        return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# Required module manifest
# ──────────────────────────────────────────────────────────────────────────────

# (module_path, human_label, is_critical)
REQUIRED_MODULES: List[tuple] = [
    # Core infrastructure
    ("quant_ecosystem.core.safety_controller",          "SafetyController",           True),
    # Market layer
    ("quant_ecosystem.market.market_data_engine",       "MarketDataEngine",           True),
    # Intelligence
    ("quant_ecosystem.intelligence.global_intelligence_engine",
                                                        "GlobalIntelligenceEngine",   True),
    # Strategy
    ("quant_ecosystem.strategy.live_strategy_engine",   "LiveStrategyEngine",         True),
    ("quant_ecosystem.strategy.strategy_bank_layer",    "StrategyBankLayer",          True),
    ("quant_ecosystem.strategy.selector_core",          "SelectorCore",               False),
    # Allocation
    ("quant_ecosystem.allocation.allocation_engine",    "AllocationEngine",           True),
    ("quant_ecosystem.allocation.diversity_engine",     "DiversityEngine",            False),
    # Survival / Safety
    ("quant_ecosystem.survival.survival_engine",        "SurvivalEngine",             True),
    # Alpha
    ("quant_ecosystem.alpha.alpha_scanner_core",        "AlphaScannerCore",           False),
    # Shadow
    ("quant_ecosystem.shadow.shadow_engine",            "ShadowEngine",               False),
    # Controller
    ("quant_ecosystem.controller.autonomous_controller","AutonomousController",       True),
    # Regime
    ("quant_ecosystem.regime.regime_ai_core",           "RegimeAICore",               False),
    # Events / Pulse
    ("quant_ecosystem.events.event_driven_signal_engine","EventDrivenSignalEngine",   False),
    ("quant_ecosystem.pulse.pulse_engine",              "PulseEngine",                False),
    # Orchestration / Governor
    ("quant_ecosystem.orchestration.event_orchestrator","EventOrchestrator",          True),
    ("quant_ecosystem.governor.governor_core",          "GovernorCore",               True),
    # Telegram
    ("quant_ecosystem.telegram.telegram_control_center","TelegramControlCenter",      False),
]

# Engine classes to instantiate-test (module_path, class_name)
ENGINE_SMOKE_TESTS: List[tuple] = [
    ("quant_ecosystem.market.market_data_engine",        "MarketDataEngine"),
    ("quant_ecosystem.intelligence.global_intelligence_engine",
                                                         "GlobalIntelligenceEngine"),
    ("quant_ecosystem.strategy.live_strategy_engine",    "LiveStrategyEngine"),
    ("quant_ecosystem.allocation.allocation_engine",     "AllocationEngine"),
    ("quant_ecosystem.survival.survival_engine",         "SurvivalEngine"),
    ("quant_ecosystem.controller.autonomous_controller", "AutonomousController"),
    ("quant_ecosystem.orchestration.event_orchestrator", "EventOrchestrator"),
    ("quant_ecosystem.governor.governor_core",           "GovernorCore"),
    ("quant_ecosystem.telegram.telegram_control_center", "TelegramControlCenter"),
]


# ──────────────────────────────────────────────────────────────────────────────
# Main diagnostic class
# ──────────────────────────────────────────────────────────────────────────────

class SystemIntegrityCheck:
    """
    Run-time diagnostic scanner for Quant Ecosystem 3.0.

    Parameters
    ----------
    mode : str
        "PAPER" (default) or "LIVE" — affects broker / market-data
        connectivity severity.
    config : dict, optional
        System config forwarded from SystemFactory.
    """

    def __init__(self, mode: str = "PAPER", config: Optional[dict] = None):
        self.mode = mode.upper()
        self.config = config or {}

    # ──────────────────────────────────────────────────────────────────
    # Master entry point
    # ──────────────────────────────────────────────────────────────────

    def run_full_diagnostic(self, router=None) -> DiagnosticReport:
        """
        Execute all integrity checks and return a consolidated
        DiagnosticReport.  Never raises — all exceptions are caught
        and recorded as CRITICAL items so the caller can decide.
        """
        report = DiagnosticReport()

        print("[SystemIntegrityCheck] Starting full diagnostic scan...")

        checks = [
            ("module_scan",      self.check_modules),
            ("engine_smoke",     self.check_engines),
            ("telegram",         self.check_telegram),
            ("broker",           self.check_broker),
            ("market_data",      self.check_market_data),
        ]

        for label, fn in checks:
            try:
                result = fn(report=report, router=router)
                report.details[label] = result or {}
            except Exception:  # never let a check crash the boot
                tb = traceback.format_exc()
                report.add_critical(f"Diagnostic '{label}' itself threw: {tb[:300]}")
                report.details[label] = {"error": tb}

        print(report.pretty())
        return report

    # ──────────────────────────────────────────────────────────────────
    # Check 1 — Module presence
    # ──────────────────────────────────────────────────────────────────

    def check_modules(self, report: DiagnosticReport, **_) -> dict:
        """
        Attempt importlib.import_module on every entry in REQUIRED_MODULES.
        Critical modules that are missing escalate to CRITICAL.
        Non-critical missing modules escalate to DEGRADED.
        """
        results: Dict[str, str] = {}

        for module_path, label, is_critical in REQUIRED_MODULES:
            try:
                importlib.import_module(module_path)
                results[label] = "OK"
            except ModuleNotFoundError as exc:
                results[label] = f"MISSING — {exc}"
                report.missing_modules.append(f"{label} ({module_path})")
                if is_critical:
                    report.add_critical(f"Critical module missing: {label}")
                else:
                    report.add_degraded(f"Optional module missing: {label}")
            except RecursionError:
                results[label] = "RECURSION ERROR on import"
                report.missing_modules.append(f"{label} ({module_path}) [RECURSION]")
                report.add_critical(
                    f"RecursionError while importing {label} — "
                    "check for self-instantiation in __init__"
                )
            except Exception as exc:
                results[label] = f"IMPORT ERROR — {exc}"
                report.missing_modules.append(f"{label} ({module_path}) [ERROR]")
                severity = "add_critical" if is_critical else "add_degraded"
                getattr(report, severity)(f"Import error in {label}: {exc}")

        return results

    # ──────────────────────────────────────────────────────────────────
    # Check 2 — Engine construction smoke-test
    # ──────────────────────────────────────────────────────────────────

    def check_engines(self, report: DiagnosticReport, **_) -> dict:
        """
        Try to instantiate each engine with (config=None).
        Catches RecursionError explicitly — the most common Ecosystem bug.
        """
        results: Dict[str, str] = {}

        for module_path, class_name in ENGINE_SMOKE_TESTS:
            label = class_name
            try:
                mod = importlib.import_module(module_path)
                cls = getattr(mod, class_name)
                # Instantiate with minimal config — must not crash
                instance = cls(config=None)
                del instance
                results[label] = "OK"
            except RecursionError:
                results[label] = "RECURSION ERROR"
                report.broken_engines.append(f"{label} [RECURSION]")
                report.add_critical(
                    f"RecursionError constructing {label} — "
                    "engine is self-instantiating in __init__"
                )
            except ModuleNotFoundError:
                results[label] = "MODULE NOT FOUND (skipped)"
                # already caught by check_modules
            except TypeError as exc:
                results[label] = f"SIGNATURE MISMATCH — {exc}"
                report.broken_engines.append(f"{label} [SIGNATURE]")
                report.add_critical(
                    f"Constructor TypeError in {label}: {exc} "
                    "— add config=None, **kwargs to __init__"
                )
            except Exception as exc:
                results[label] = f"ERROR — {exc}"
                report.broken_engines.append(f"{label} [ERROR: {exc}]")
                report.add_degraded(f"Unexpected error constructing {label}: {exc}")

        return results

    # ──────────────────────────────────────────────────────────────────
    # Check 3 — Telegram connectivity
    # ──────────────────────────────────────────────────────────────────

    def check_telegram(self, report: DiagnosticReport, router=None, **_) -> dict:
        """
        Verify Telegram engine exists and, if credentials are present,
        that the Bot API endpoint is reachable.
        Telegram failure is never CRITICAL — system can trade without it.
        """
        result: Dict[str, Any] = {}

        try:
            mod = importlib.import_module(
                "quant_ecosystem.telegram.telegram_control_center"
            )
            tcc_cls = getattr(mod, "TelegramControlCenter")
        except Exception as exc:
            report.add_warning(f"TelegramControlCenter unavailable: {exc}")
            result["status"] = "UNAVAILABLE"
            return result

        token = self.config.get("TELEGRAM_TOKEN")
        chat_id = self.config.get("TELEGRAM_CHAT_ID")

        if not token or not chat_id:
            result["status"] = "LOG_ONLY"
            result["reason"] = "TELEGRAM_TOKEN / TELEGRAM_CHAT_ID not in config"
            report.add_warning("Telegram running in LOG-ONLY mode (no credentials).")
            return result

        # Credentials present — do a live getMe probe
        try:
            import requests  # lazy
            url = f"https://api.telegram.org/bot{token}/getMe"
            resp = requests.get(url, timeout=5)
            if resp.ok:
                result["status"] = "CONNECTED"
                result["bot"] = resp.json().get("result", {}).get("username", "?")
            else:
                result["status"] = "AUTH_FAILED"
                result["http_status"] = resp.status_code
                report.add_degraded(
                    f"Telegram getMe returned HTTP {resp.status_code} — check token."
                )
        except ImportError:
            result["status"] = "LOG_ONLY"
            result["reason"] = "`requests` not installed"
            report.add_warning("Telegram: `requests` not installed — LOG-ONLY.")
        except Exception as exc:
            result["status"] = "UNREACHABLE"
            result["error"] = str(exc)
            report.add_degraded(f"Telegram API unreachable: {exc}")

        return result

    # ──────────────────────────────────────────────────────────────────
    # Check 4 — Broker connectivity
    # ──────────────────────────────────────────────────────────────────

    def check_broker(self, report: DiagnosticReport, router=None, **_) -> dict:
        """
        In PAPER mode: broker is simulated — always passes.
        In LIVE mode: probe the broker object on the router for
        is_connected() / ping() or equivalent.
        """
        result: Dict[str, Any] = {"mode": self.mode}

        if self.mode == "PAPER":
            result["status"] = "SIMULATED"
            result["note"] = "Broker check skipped in PAPER mode."
            return result

        # LIVE mode — try to reach broker via router
        broker = None
        if router is not None:
            broker = (
                getattr(router, "broker", None)
                or getattr(router, "execution_router", None)
                or getattr(router, "broker_engine", None)
            )

        if broker is None:
            report.add_critical(
                "LIVE mode: broker not found on router — cannot execute orders."
            )
            result["status"] = "NOT_FOUND"
            return result

        # Probe common connectivity methods
        for method_name in ("is_connected", "ping", "status"):
            probe = getattr(broker, method_name, None)
            if callable(probe):
                try:
                    val = probe()
                    result["status"] = "CONNECTED" if val else "DISCONNECTED"
                    result["probe_method"] = method_name
                    if not val:
                        report.add_critical(
                            f"LIVE broker reports disconnected via {method_name}()."
                        )
                    return result
                except Exception as exc:
                    result["probe_error"] = str(exc)
                    report.add_critical(f"Broker probe '{method_name}' failed: {exc}")
                    result["status"] = "PROBE_FAILED"
                    return result

        # No recognisable probe method
        result["status"] = "UNKNOWN"
        report.add_warning(
            "Broker object found but no is_connected/ping/status method — "
            "cannot verify connectivity."
        )
        return result

    # ──────────────────────────────────────────────────────────────────
    # Check 5 — Market data feed
    # ──────────────────────────────────────────────────────────────────

    def check_market_data(self, report: DiagnosticReport, router=None, **_) -> dict:
        """
        Verify MarketDataEngine is importable, constructible, and — if
        running LIVE — that its feed attribute is not None.
        """
        result: Dict[str, Any] = {"mode": self.mode}

        # Import check
        try:
            mod = importlib.import_module("quant_ecosystem.market.market_data_engine")
            mde_cls = getattr(mod, "MarketDataEngine")
        except Exception as exc:
            report.add_critical(f"MarketDataEngine import failed: {exc}")
            result["status"] = "IMPORT_FAILED"
            return result

        # Recursion guard — instantiate with sentinel config
        try:
            probe_instance = mde_cls(config=None, universe=[])
        except RecursionError:
            report.add_critical(
                "MarketDataEngine is still self-instantiating — apply BUG #1 patch."
            )
            result["status"] = "RECURSION"
            return result
        except Exception as exc:
            report.add_critical(f"MarketDataEngine construction error: {exc}")
            result["status"] = "CONSTRUCT_FAILED"
            return result

        result["import_ok"] = True
        result["construct_ok"] = True

        # In LIVE mode check that a real feed is wired
        if self.mode == "LIVE":
            live_mde = None
            if router is not None:
                live_mde = getattr(router, "market_data", None)

            if live_mde is None:
                report.add_critical(
                    "LIVE mode: MarketDataEngine not found on router — no market data."
                )
                result["status"] = "NOT_WIRED"
            elif getattr(live_mde, "feed", None) is None:
                report.add_degraded(
                    "LIVE mode: MarketDataEngine.feed is None — "
                    "data feed not yet started."
                )
                result["status"] = "FEED_NOT_STARTED"
            else:
                result["status"] = "LIVE_OK"
        else:
            result["status"] = "PAPER_OK"

        return result

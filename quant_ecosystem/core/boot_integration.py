"""
quant_ecosystem/core/boot_integration.py
=========================================
Boot-sequence integration helper for SystemIntegrityCheck + SafetyController.
Quant Ecosystem 3.0

HOW TO USE
----------
This module exposes a single convenience function:

    run_boot_diagnostics(router, config, mode) -> SafetyController

Drop the following block into your existing boot sequence IMMEDIATELY
after SystemFactory/SystemRouter finish building the engine graph:

────────────────────────────────────────────────────────────────────
# === INTEGRITY & SAFETY BOOT BLOCK (insert after router.build()) ===

from quant_ecosystem.core.boot_integration import run_boot_diagnostics

safety = run_boot_diagnostics(router=router, config=config, mode=mode)

# Safety is now live.  Pass it to MasterOrchestrator if needed.
orchestrator = MasterOrchestrator(router=router, safety=safety)
orchestrator.run()
────────────────────────────────────────────────────────────────────

The block NEVER raises — boot will always proceed to MasterOrchestrator.
CRITICAL diagnostics call sys.exit(1) ONLY when mode == "LIVE".
In PAPER mode, CRITICAL findings print a banner but allow boot to continue.
"""

from __future__ import annotations

import sys
from typing import Optional

# Lazy imports keep this module importable even if sub-engines are broken
_INTEGRITY_MODULE = "quant_ecosystem.core.system_integrity_check"
_SAFETY_MODULE    = "quant_ecosystem.core.safety_controller"


# ──────────────────────────────────────────────────────────────────────────────
# Public boot helper
# ──────────────────────────────────────────────────────────────────────────────

def run_boot_diagnostics(
    router,
    config:          Optional[dict] = None,
    mode:            str            = "PAPER",
    halt_on_critical: bool          = True,
) -> object:
    """
    Run SystemIntegrityCheck, wire SafetyController, return the controller.

    Parameters
    ----------
    router            : SystemRouter instance (fully built)
    config            : system config dict
    mode              : "PAPER" | "LIVE"
    halt_on_critical  : if True AND mode == "LIVE", call sys.exit(1) on CRITICAL

    Returns
    -------
    SafetyController instance (already registered with router)
    """
    config = config or {}
    mode   = config.get("mode", mode).upper()

    # ── Step 1: Run integrity diagnostics ────────────────────────────
    report = _run_integrity(router=router, config=config, mode=mode)

    # ── Step 2: React to system status ───────────────────────────────
    if report is not None:
        status = getattr(report, "system_status", "UNKNOWN")

        if status == "CRITICAL":
            _print_critical_banner(report)
            if mode == "LIVE" and halt_on_critical:
                print(
                    "[boot_integration] CRITICAL in LIVE mode — "
                    "refusing to start. Fix reported issues and retry."
                )
                sys.exit(1)
            else:
                print(
                    "[boot_integration] CRITICAL detected but mode=PAPER — "
                    "boot continues with degraded functionality."
                )

        elif status == "DEGRADED":
            print(
                "[boot_integration] ⚠️  System is DEGRADED — "
                "non-critical modules missing. Boot continues."
            )

        else:
            print("[boot_integration] ✓ Integrity check PASSED — system HEALTHY.")

    # ── Step 3: Build and wire SafetyController ───────────────────────
    safety = _build_safety(router=router, config=config, mode=mode)

    # ── Step 4: Register shutdown hook for emergency teardown ─────────
    if safety is not None and report is not None:
        if getattr(report, "system_status", "HEALTHY") == "CRITICAL" and mode == "LIVE":
            # Wire emergency_shutdown as the router's stop handler
            stop_fn = getattr(router, "stop", None)
            if callable(stop_fn):
                safety.register_shutdown_hook(stop_fn)

    print(
        f"[boot_integration] Boot diagnostics complete | "
        f"status={getattr(report, 'system_status', 'N/A')} | mode={mode}"
    )

    return safety


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers (all wrapped in broad try/except — must never raise)
# ──────────────────────────────────────────────────────────────────────────────

def _run_integrity(router, config: dict, mode: str):
    """Import and run SystemIntegrityCheck. Returns report or None on error."""
    try:
        import importlib
        mod     = importlib.import_module(_INTEGRITY_MODULE)
        cls     = getattr(mod, "SystemIntegrityCheck")
        checker = cls(mode=mode, config=config)
        return checker.run_full_diagnostic(router)
    except Exception as exc:
        print(f"[boot_integration] SystemIntegrityCheck unavailable: {exc}")
        return None


def _build_safety(router, config: dict, mode: str):
    """Import, instantiate and wire SafetyController. Returns instance or None."""
    try:
        import importlib
        mod    = importlib.import_module(_SAFETY_MODULE)
        cls    = getattr(mod, "SafetyController")
        safety = cls(config=config, mode=mode)
        safety.register_router(router)

        # Attach to router so other engines can reach it
        try:
            router.safety = safety
        except Exception:
            pass  # router may be read-only — not fatal

        print("[boot_integration] SafetyController wired to router.")
        return safety
    except Exception as exc:
        print(f"[boot_integration] SafetyController unavailable: {exc}")
        return None


def _print_critical_banner(report) -> None:
    print("\n" + "═" * 60)
    print("  ❌  SYSTEM INTEGRITY — CRITICAL")
    print("═" * 60)
    for item in getattr(report, "missing_modules", []):
        print(f"  MISSING : {item}")
    for item in getattr(report, "broken_engines", []):
        print(f"  BROKEN  : {item}")
    for warn in getattr(report, "warnings", []):
        if "[CRITICAL]" in warn:
            print(f"  {warn}")
    print("═" * 60 + "\n")

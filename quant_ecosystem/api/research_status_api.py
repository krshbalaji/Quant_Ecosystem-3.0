"""
quant_ecosystem/api/research_status_api.py
==========================================
Research Status API — Quant Ecosystem 3.0

Lightweight, dependency-free HTTP JSON API that exposes the current
state of the research system.  Built entirely on Python's stdlib
``http.server`` — no Flask, no FastAPI, no external dependencies.

Runs in a background daemon thread.  Never blocks trading.

Architecture
------------

    ┌──────────────────────────────────────────────────────────────────┐
    │              ResearchStatusAPI                                   │
    │              (daemon thread, HTTP server)                        │
    └──────────────┬──────────────────────────────────────────────────┘
                   │  reads (never writes)
    ┌──────────────▼──────────────────────────────────────────────────┐
    │                     SystemRouter                                │
    │  autonomous_research_loop · research_grid · meta_research_ai   │
    │  strategy_registry · alpha_bank · capital_intelligence         │
    │  mutation_engine · regime_intelligence · state                 │
    └─────────────────────────────────────────────────────────────────┘

Endpoints
---------
    GET  /                      → redirect to /status
    GET  /status                → full system health snapshot
    GET  /research              → research loop + grid stats
    GET  /strategies            → strategy registry summary
    GET  /alpha                 → alpha bank top genomes
    GET  /capital               → capital allocation snapshot
    GET  /regime                → current market regime
    GET  /mutation              → mutation engine stats
    GET  /cycle/last            → most recent research cycle detail
    GET  /cycle/history         → last N research cycle records
    GET  /feature-lab           → feature lab extractor list + importance
    GET  /health                → simple liveness probe (returns {"ok":true})

All responses are JSON with Content-Type: application/json.
CORS headers are included (Access-Control-Allow-Origin: *) so the API
can be consumed by a dashboard running on any origin.

Error responses use standard HTTP status codes with a JSON body:
    {"error": "message", "endpoint": "/path", "timestamp": <epoch>}

Configuration
-------------
    host            bind address   (default "127.0.0.1")
    port            listen port    (default 7075)
    history_limit   max cycles in /cycle/history response   (default 20)
    pretty_json     indent JSON for readability             (default False)
    cors_origins    CORS origin header value                (default "*")

Usage
-----
    api = ResearchStatusAPI(router=system_router, port=7075)
    api.start()          # launches daemon thread — non-blocking
    ...
    api.stop()           # graceful shutdown
"""

from __future__ import annotations

import http.server
import json
import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_TAG = "[research_api]"


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class APIConfig:
    host:          str   = "127.0.0.1"
    port:          int   = 7075
    history_limit: int   = 20
    pretty_json:   bool  = False
    cors_origins:  str   = "*"

    def __post_init__(self) -> None:
        self.port          = max(1024, min(65535, int(self.port)))
        self.history_limit = max(1, int(self.history_limit))


# ─────────────────────────────────────────────────────────────────────────────
# Route handlers — pure functions, receive router, return dict
# ─────────────────────────────────────────────────────────────────────────────

class _Routes:
    """
    Each method handles one API endpoint.
    Returns a (status_code, dict) tuple.
    """

    def __init__(self, router: Any, cfg: APIConfig) -> None:
        self._r   = router
        self._cfg = cfg

    # ── /health ───────────────────────────────────────────────────────────────

    def health(self) -> tuple:
        return 200, {"ok": True, "timestamp": _now()}

    # ── /status ───────────────────────────────────────────────────────────────

    def status(self) -> tuple:
        r = self._r
        out: Dict[str, Any] = {"timestamp": _now()}

        # Mode
        out["mode"] = str(getattr(getattr(r, "config", None), "mode", "UNKNOWN"))

        # Trading state
        state = getattr(r, "state", None)
        if state:
            out["trading_halted"] = bool(getattr(state, "trading_halted", False))
            out["auto_mode"]      = bool(getattr(state, "auto_mode", False))
            out["current_regime"] = str(getattr(state, "current_regime", "UNKNOWN"))
        else:
            out["trading_halted"] = None
            out["auto_mode"]      = None
            out["current_regime"] = "UNKNOWN"

        # Research loop quick status
        loop = getattr(r, "autonomous_research_loop", None)
        out["research_loop_running"] = bool(
            loop and getattr(loop, "is_running", False)
        )

        # Strategy count
        registry = getattr(r, "strategy_registry", None)
        out["strategy_count"] = _safe_call(lambda: registry.count()) if registry else 0

        # Capital
        cap = getattr(r, "capital_intelligence", None)
        if cap and hasattr(cap, "capital_snapshot"):
            snap = _safe_call(lambda: cap.capital_snapshot()) or {}
            out["total_capital"] = snap.get("total_capital", 0)

        return 200, out

    # ── /research ─────────────────────────────────────────────────────────────

    def research(self) -> tuple:
        r   = self._r
        out: Dict[str, Any] = {"timestamp": _now()}

        loop = getattr(r, "autonomous_research_loop", None)
        if loop:
            loop_status = _safe_call(lambda: loop.status()) or {}
            out["loop"] = loop_status

            last = getattr(loop, "last_cycle", None)
            if last and hasattr(last, "to_dict"):
                out["last_cycle"] = _safe_call(lambda: last.to_dict()) or {}
        else:
            out["loop"] = {"available": False}

        grid = getattr(r, "research_grid", None)
        if grid and hasattr(grid, "status"):
            out["grid"] = _safe_call(lambda: grid.status()) or {}
        else:
            out["grid"] = {"available": False}

        meta = getattr(r, "meta_research_ai", None)
        if meta:
            pri = getattr(meta, "last_priorities", None)
            if pri:
                out["meta_priorities"] = {
                    "focus_family":   getattr(pri, "focus_family",   "?"),
                    "regime_bias":    getattr(pri, "regime_bias",    "?"),
                    "mutation_rate":  getattr(pri, "mutation_rate",  0),
                    "batch_size":     getattr(pri, "batch_size",     0),
                    "confidence":     getattr(pri, "confidence",     0),
                    "reasoning":      getattr(pri, "reasoning",      ""),
                    "generated_at":   getattr(pri, "generated_at",   0),
                }
            else:
                out["meta_priorities"] = {"available": False}

        return 200, out

    # ── /strategies ───────────────────────────────────────────────────────────

    def strategies(self) -> tuple:
        r   = self._r
        out: Dict[str, Any] = {"timestamp": _now()}

        registry = getattr(r, "strategy_registry", None)
        if registry:
            out["count"]      = _safe_call(lambda: registry.count()) or 0
            strategies_list   = _safe_call(lambda: registry.all()) or []
            out["strategy_ids"] = [
                getattr(s, "id", getattr(s, "STRATEGY_ID", str(s)))
                for s in strategies_list[:50]
            ]
        else:
            out["count"]        = 0
            out["strategy_ids"] = []

        # Active strategies
        selector = getattr(r, "strategy_selector", None)
        if selector and hasattr(selector, "active_strategies"):
            active = _safe_call(lambda: list(selector.active_strategies)) or []
            out["active_count"] = len(active)
            out["active_ids"]   = [
                getattr(s, "id", getattr(s, "STRATEGY_ID", str(s)))
                for s in active[:20]
            ]

        return 200, out

    # ── /alpha ────────────────────────────────────────────────────────────────

    def alpha(self) -> tuple:
        r   = self._r
        out: Dict[str, Any] = {"timestamp": _now()}

        bank = getattr(r, "alpha_bank", None)
        if bank:
            if hasattr(bank, "top"):
                out["top_genomes"] = _safe_call(lambda: bank.top(n=10)) or []
            if hasattr(bank, "size"):
                out["size"] = _safe_call(lambda: bank.size()) or 0
            if hasattr(bank, "stats"):
                out["stats"] = _safe_call(lambda: bank.stats()) or {}
        else:
            out["available"] = False

        return 200, out

    # ── /capital ──────────────────────────────────────────────────────────────

    def capital(self) -> tuple:
        r   = self._r
        out: Dict[str, Any] = {"timestamp": _now()}

        cap = getattr(r, "capital_intelligence", None)
        if cap:
            if hasattr(cap, "capital_snapshot"):
                out["snapshot"] = _safe_call(lambda: cap.capital_snapshot()) or {}
            # Last allocation if available
            if hasattr(cap, "last_allocation"):
                out["last_allocation"] = _safe_call(lambda: cap.last_allocation) or {}
        else:
            out["available"] = False

        return 200, out

    # ── /regime ───────────────────────────────────────────────────────────────

    def regime(self) -> tuple:
        r   = self._r
        out: Dict[str, Any] = {"timestamp": _now()}

        for attr in ("regime_intelligence", "regime_ai_engine", "market_regime_detector"):
            eng = getattr(r, attr, None)
            if eng:
                if hasattr(eng, "get_regime"):
                    out["current_regime"] = _safe_call(lambda: eng.get_regime()) or "UNKNOWN"
                if hasattr(eng, "current_regime"):
                    out["current_regime"] = str(getattr(eng, "current_regime", "UNKNOWN"))
                if hasattr(eng, "detect_transition"):
                    out["transition_state"] = _safe_call(
                        lambda: str(eng.detect_transition({}))
                    )
                break
        else:
            # Fallback to state
            state = getattr(r, "state", None)
            out["current_regime"] = str(getattr(state, "current_regime", "UNKNOWN")) if state else "UNKNOWN"

        return 200, out

    # ── /mutation ─────────────────────────────────────────────────────────────

    def mutation(self) -> tuple:
        r   = self._r
        out: Dict[str, Any] = {"timestamp": _now()}

        eng = getattr(r, "mutation_engine", None)
        if eng and hasattr(eng, "stats"):
            out["stats"] = _safe_call(lambda: eng.stats()) or {}
        else:
            out["available"] = False

        return 200, out

    # ── /cycle/last ───────────────────────────────────────────────────────────

    def cycle_last(self) -> tuple:
        loop = getattr(self._r, "autonomous_research_loop", None)
        if not loop:
            return 404, {"error": "Research loop not available"}

        last = getattr(loop, "last_cycle", None)
        if not last:
            return 404, {"error": "No cycle completed yet"}

        if hasattr(last, "to_dict"):
            return 200, last.to_dict()
        return 200, {"cycle": str(last), "timestamp": _now()}

    # ── /cycle/history ────────────────────────────────────────────────────────

    def cycle_history(self) -> tuple:
        loop = getattr(self._r, "autonomous_research_loop", None)
        if not loop:
            return 404, {"error": "Research loop not available"}

        history = list(getattr(loop, "cycle_history", []))
        limit   = self._cfg.history_limit
        trimmed = history[-limit:]

        records = []
        for c in trimmed:
            if hasattr(c, "to_dict"):
                records.append(c.to_dict())
            else:
                records.append({"cycle": str(c)})

        return 200, {"count": len(records), "cycles": records, "timestamp": _now()}

    # ── /feature-lab ──────────────────────────────────────────────────────────

    def feature_lab(self) -> tuple:
        r   = self._r
        out: Dict[str, Any] = {"timestamp": _now()}

        lab = getattr(r, "feature_lab", None)
        if lab and hasattr(lab, "status"):
            out.update(_safe_call(lambda: lab.status()) or {})
            if hasattr(lab, "importance_scores"):
                scores = _safe_call(lambda: lab.importance_scores()) or {}
                # Return top 20 sorted
                top = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:20]
                out["top_features"] = [{"name": k, "score": round(v, 4)} for k, v in top]
        else:
            out["available"] = False

        return 200, out


# ─────────────────────────────────────────────────────────────────────────────
# HTTP request handler
# ─────────────────────────────────────────────────────────────────────────────

def _make_handler(routes: "_Routes", cfg: APIConfig):
    """Factory: produce an http.server.BaseHTTPRequestHandler subclass."""

    class _Handler(http.server.BaseHTTPRequestHandler):

        def log_message(self, fmt: str, *args) -> None:  # suppress default logs
            logger.debug("%s HTTP %s", _TAG, fmt % args)

        def do_GET(self) -> None:
            path = urlparse(self.path).path.rstrip("/") or "/"

            # Route dispatch
            dispatch: Dict[str, Callable] = {
                "/":                 routes.status,
                "/status":           routes.status,
                "/health":           routes.health,
                "/research":         routes.research,
                "/strategies":       routes.strategies,
                "/alpha":            routes.alpha,
                "/capital":          routes.capital,
                "/regime":           routes.regime,
                "/mutation":         routes.mutation,
                "/cycle/last":       routes.cycle_last,
                "/cycle/history":    routes.cycle_history,
                "/feature-lab":      routes.feature_lab,
            }

            handler = dispatch.get(path)
            if handler is None:
                status, body = 404, {
                    "error":     f"Unknown endpoint: {path}",
                    "endpoints": sorted(dispatch.keys()),
                    "timestamp": _now(),
                }
            else:
                try:
                    status, body = handler()
                except Exception as exc:
                    logger.exception("%s Handler error for %s: %s", _TAG, path, exc)
                    status, body = 500, {
                        "error":     str(exc),
                        "endpoint":  path,
                        "timestamp": _now(),
                    }

            indent = 2 if cfg.pretty_json else None
            payload = json.dumps(body, indent=indent, default=str).encode()

            self.send_response(status)
            self.send_header("Content-Type",  "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Access-Control-Allow-Origin", cfg.cors_origins)
            self.send_header("Cache-Control",  "no-cache")
            self.end_headers()
            self.wfile.write(payload)

        def do_OPTIONS(self) -> None:
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin",  cfg.cors_origins)
            self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

    return _Handler


# ─────────────────────────────────────────────────────────────────────────────
# ResearchStatusAPI
# ─────────────────────────────────────────────────────────────────────────────

class ResearchStatusAPI:
    """
    Lightweight HTTP JSON API for real-time research system monitoring.

    Serves read-only JSON responses from a background daemon thread.
    Zero external dependencies — built on Python stdlib http.server.

    Parameters
    ----------
    router  : SystemRouter (or any object exposing the subsystem attributes)
    host    : bind address   (default "127.0.0.1")
    port    : listen port    (default 7075)
    cfg     : APIConfig override
    """

    def __init__(
        self,
        router: Any                   = None,
        host:   str                   = "127.0.0.1",
        port:   int                   = 7075,
        cfg:    Optional[APIConfig]   = None,
        **kwargs,
    ) -> None:

        self._router = router
        self._cfg    = cfg or APIConfig(host=host, port=port)
        self._server: Optional[http.server.HTTPServer] = None
        self._thread: Optional[threading.Thread]       = None

        logger.info(
            "%s ResearchStatusAPI configured | %s:%s",
            _TAG, self._cfg.host, self._cfg.port,
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def attach_router(self, router: Any) -> None:
        """Inject or replace the SystemRouter reference."""
        self._router = router

    def start(self) -> bool:
        """
        Start the HTTP server in a background daemon thread.
        Non-blocking.  Idempotent.

        Returns True if started, False if already running.
        """
        if self._thread and self._thread.is_alive():
            logger.debug("%s Already running.", _TAG)
            return False

        routes  = _Routes(self._router, self._cfg)
        handler = _make_handler(routes, self._cfg)

        try:
            self._server = http.server.HTTPServer(
                (self._cfg.host, self._cfg.port),
                handler,
            )
            self._server.timeout = 1.0  # poll interval for clean shutdown
        except OSError as exc:
            logger.error("%s Failed to bind %s:%s — %s", _TAG, self._cfg.host, self._cfg.port, exc)
            return False

        self._thread = threading.Thread(
            target=self._serve_forever,
            name="ResearchStatusAPI",
            daemon=True,
        )
        self._thread.start()

        logger.info(
            "%s HTTP server started on http://%s:%s",
            _TAG, self._cfg.host, self._cfg.port,
        )
        return True

    def stop(self) -> None:
        """Gracefully shut down the HTTP server."""
        if self._server:
            self._server.shutdown()
            logger.info("%s HTTP server stopped.", _TAG)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def url(self) -> str:
        return f"http://{self._cfg.host}:{self._cfg.port}"

    def status(self) -> Dict[str, Any]:
        return {
            "running": self.is_running,
            "url":     self.url,
            "host":    self._cfg.host,
            "port":    self._cfg.port,
        }

    # ── Internal ──────────────────────────────────────────────────────────────

    def _serve_forever(self) -> None:
        logger.debug("%s Serve-forever loop started.", _TAG)
        try:
            self._server.serve_forever()
        except Exception as exc:
            logger.warning("%s Server loop exited: %s", _TAG, exc)
        logger.debug("%s Serve-forever loop exited.", _TAG)

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def from_config(cls, config: Any, router: Any = None) -> "ResearchStatusAPI":
        """
        Build from a system config object that may expose:
            config.api_host
            config.api_port
            config.api_pretty_json
        """
        return cls(
            router = router,
            cfg    = APIConfig(
                host        = str(getattr(config, "api_host",        "127.0.0.1")),
                port        = int(getattr(config, "api_port",        7075)),
                pretty_json = bool(getattr(config, "api_pretty_json", False)),
            ),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _now() -> float:
    return time.time()


def _safe_call(fn: Callable, default: Any = None) -> Any:
    try:
        return fn()
    except Exception as exc:
        logger.debug("%s _safe_call error: %s", _TAG, exc)
        return default

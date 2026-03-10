from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from quant_ecosystem.communication.telegram_commands import CommandParser

logger = logging.getLogger(__name__)


@dataclass
class CommandResult:
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class TelegramControlCenter:
    def __init__(
        self,
        system_router: Optional[Any] = None,
        research_grid: Optional[Any] = None,
        autonomous_loop: Optional[Any] = None,
        alpha_bank: Optional[Any] = None,
        authorized_users: Optional[List[str]] = None,
    ) -> None:
        self.system_router = system_router
        self.research_grid = research_grid
        self.autonomous_loop = autonomous_loop
        self.alpha_bank = alpha_bank
        self.authorized_users = {str(user_id) for user_id in (authorized_users or [])}
        self._lock = threading.RLock()
        self._parser = CommandParser()
        logger.info("[telegram] control center initialized")

    def is_authorized(self, user_id: str) -> bool:
        return not self.authorized_users or str(user_id) in self.authorized_users

    def execute(
        self,
        command: str,
        user_id: Optional[str] = None,
        args: Optional[List[str]] = None,
    ) -> CommandResult:
        parsed = self._parser.parse(command)
        if not parsed.valid:
            return CommandResult(False, parsed.error or "Invalid command", error=parsed.error)

        if user_id and not self.is_authorized(user_id):
            return CommandResult(False, "Unauthorized", error="unauthorized")

        if args:
            parsed.args = list(args)

        routes = {
            "status": self.status,
            "start": self.start_trading,
            "stop": self.stop_trading,
            "pause": self.pause_research,
            "resume": self.resume_research,
            "positions": self.positions,
            "pnl": self.pnl,
            "strategies": self.strategies,
            "research": self.research,
            "shutdown": self.shutdown,
            "help": self.help,
        }

        handler = routes.get(parsed.command or "")
        if handler is None:
            return CommandResult(False, f"Unknown command: /{parsed.command}", error="unknown_command")

        try:
            return handler(*parsed.args)
        except TypeError:
            return CommandResult(False, f"Usage error for /{parsed.command}", error="usage_error")
        except Exception as exc:
            logger.exception("[telegram] command failed: /%s", parsed.command)
            return CommandResult(False, f"Command failed: {exc}", error=str(exc))

    def status(self) -> CommandResult:
        router = self.system_router
        state = getattr(router, "state", None)
        loop_status = self._loop_status()
        strategy_count = self._strategy_count()

        lines = [
            "SYSTEM STATUS",
            f"Trading: {'RUNNING' if not getattr(state, 'trading_halted', False) else 'STOPPED'}",
            f"Research loop: {'RUNNING' if loop_status.get('is_running') else 'PAUSED'}",
            f"Registered strategies: {strategy_count}",
            f"Research cycles: {loop_status.get('cycle_number', 0)}",
            f"Updated: {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        ]

        if state is not None:
            lines.append(f"Equity: {float(getattr(state, 'equity', 0.0) or 0.0):,.2f}")
            lines.append(f"Cash: {float(getattr(state, 'cash', 0.0) or 0.0):,.2f}")

        return CommandResult(True, "\n".join(lines), data={"research": loop_status})

    def start_trading(self) -> CommandResult:
        router = self.system_router
        state = getattr(router, "state", None)
        if state is None:
            return CommandResult(False, "Trading state unavailable", error="missing_state")

        state.trading_halted = False
        if hasattr(router, "set_auto_mode"):
            router.set_auto_mode(True)
        logger.info("[telegram] trading started")
        return CommandResult(True, "Trading started")

    def stop_trading(self) -> CommandResult:
        router = self.system_router
        if router is None:
            return CommandResult(False, "System router unavailable", error="missing_router")

        if hasattr(router, "stop_trading"):
            router.stop_trading()
        else:
            state = getattr(router, "state", None)
            if state is not None:
                state.trading_halted = True
        logger.info("[telegram] trading stopped")
        return CommandResult(True, "Trading stopped")

    def pause_research(self) -> CommandResult:
        loop = self.autonomous_loop
        if loop is None:
            return CommandResult(False, "Research loop unavailable", error="missing_loop")
        if not getattr(loop, "is_running", False):
            return CommandResult(True, "Research loop already paused")
        loop.stop()
        logger.info("[telegram] [research_loop] paused")
        return CommandResult(True, "Research loop paused")

    def resume_research(self) -> CommandResult:
        loop = self.autonomous_loop
        if loop is None:
            return CommandResult(False, "Research loop unavailable", error="missing_loop")
        if getattr(loop, "is_running", False):
            return CommandResult(True, "Research loop already running")
        loop.start()
        logger.info("[telegram] [research_loop] resumed")
        return CommandResult(True, "Research loop resumed")

    def positions(self) -> CommandResult:
        router = self.system_router
        state = getattr(router, "state", None)
        payload = self._safe_call(getattr(router, "get_positions", None), default={}) if router else {}
        positions = payload.get("positions", {}) if isinstance(payload, dict) else {}

        lines = [
            "POSITIONS",
            f"Open positions: {int(getattr(state, 'open_positions', 0) or 0)}",
            f"Broker positions: {int(getattr(state, 'broker_positions_count', 0) or 0)}",
        ]

        if isinstance(positions, dict) and positions:
            for symbol, value in list(positions.items())[:10]:
                lines.append(f"{symbol}: {value}")
        else:
            lines.append("No position details available")

        return CommandResult(True, "\n".join(lines), data={"positions": positions})

    def pnl(self) -> CommandResult:
        state = getattr(self.system_router, "state", None)
        if state is None:
            return CommandResult(False, "P&L unavailable", error="missing_state")

        realized = float(getattr(state, "realized_pnl", 0.0) or 0.0)
        unrealized = float(getattr(state, "unrealized_pnl", 0.0) or 0.0)
        equity = float(getattr(state, "equity", 0.0) or 0.0)
        cash = float(getattr(state, "cash", 0.0) or 0.0)
        total = realized + unrealized

        lines = [
            "PNL",
            f"Realized: {realized:,.2f}",
            f"Unrealized: {unrealized:,.2f}",
            f"Total: {total:,.2f}",
            f"Equity: {equity:,.2f}",
            f"Cash: {cash:,.2f}",
        ]
        return CommandResult(True, "\n".join(lines), data={"realized": realized, "unrealized": unrealized})

    def strategies(self) -> CommandResult:
        active = self._active_strategies()
        lines = [
            "STRATEGIES",
            f"Running strategies: {len(active)}",
        ]
        lines.extend(active[:20] or ["No active strategies"])
        return CommandResult(True, "\n".join(lines), data={"strategies": active})

    def research(self) -> CommandResult:
        loop_status = self._loop_status()
        last_cycle = loop_status.get("last_cycle") or {}
        discovered = self._discovered_strategies()
        active_genomes = self._active_genomes()

        lines = [
            "RESEARCH",
            f"Research cycle number: {loop_status.get('cycle_number', 0)}",
            f"Active genomes: {active_genomes}",
            f"Best fitness: {float(last_cycle.get('best_fitness', 0.0) or 0.0):.4f}",
            f"Strategies discovered: {discovered}",
        ]

        best_genome = last_cycle.get("best_genome_id")
        if best_genome:
            lines.append(f"Best genome: {best_genome}")

        return CommandResult(
            True,
            "\n".join(lines),
            data={
                "research_cycle_number": loop_status.get("cycle_number", 0),
                "active_genomes": active_genomes,
                "best_fitness": float(last_cycle.get("best_fitness", 0.0) or 0.0),
                "strategies_discovered": discovered,
            },
        )

    def shutdown(self) -> CommandResult:
        router = self.system_router
        governor = getattr(router, "safety_governor", None) if router else None
        if governor is not None and hasattr(governor, "emergency_shutdown"):
            governor.emergency_shutdown("Triggered from Telegram /shutdown")
            logger.warning("[telegram] emergency shutdown triggered through safety governor")
            return CommandResult(True, "Emergency shutdown triggered")

        if self.autonomous_loop is not None and getattr(self.autonomous_loop, "is_running", False):
            self.autonomous_loop.stop()

        if router is not None and hasattr(router, "stop_trading"):
            router.stop_trading()

        logger.warning("[telegram] emergency shutdown fallback triggered")
        return CommandResult(True, "Emergency shutdown triggered")

    def help(self) -> CommandResult:
        return CommandResult(
            True,
            "\n".join(
                [
                    "AVAILABLE COMMANDS",
                    "/status",
                    "/start",
                    "/stop",
                    "/pause",
                    "/resume",
                    "/positions",
                    "/pnl",
                    "/strategies",
                    "/research",
                    "/shutdown",
                ]
            ),
        )

    def _loop_status(self) -> Dict[str, Any]:
        loop = self.autonomous_loop
        if loop is None or not hasattr(loop, "status"):
            return {"is_running": False, "cycle_number": 0, "last_cycle": None}
        return self._safe_call(loop.status, default={"is_running": False, "cycle_number": 0, "last_cycle": None})

    def _strategy_count(self) -> int:
        registry = getattr(self.system_router, "strategy_registry", None)
        if registry is not None and hasattr(registry, "count"):
            return int(self._safe_call(registry.count, default=0) or 0)
        return len(self._active_strategies())

    def _active_strategies(self) -> List[str]:
        engine = getattr(self.system_router, "strategy_engine", None)
        if engine is not None and hasattr(engine, "get_active_strategies"):
            strategies = self._safe_call(engine.get_active_strategies, default=[])
        else:
            registry = getattr(self.system_router, "strategy_registry", None)
            strategies = self._safe_call(registry.load, default=[]) if registry is not None else []

        names: List[str] = []
        for strategy in strategies or []:
            strategy_id = getattr(strategy, "STRATEGY_ID", None) or getattr(strategy, "id", None)
            if strategy_id:
                names.append(str(strategy_id))
        return names

    def _discovered_strategies(self) -> int:
        if self.alpha_bank is not None:
            stats = self._safe_call(self.alpha_bank.get_stats, default={})
            if isinstance(stats, dict):
                return int(stats.get("total_strategies", 0) or 0)
        return self._strategy_count()

    def _active_genomes(self) -> int:
        if self.research_grid is None or not hasattr(self.research_grid, "status"):
            return 0

        status = self._safe_call(self.research_grid.status, default={})
        if not isinstance(status, dict):
            return 0

        candidates = [
            status.get("active_genomes"),
            status.get("queued"),
            status.get("running"),
        ]
        scheduler = status.get("scheduler")
        if isinstance(scheduler, dict):
            candidates.extend(
                [
                    scheduler.get("queued"),
                    scheduler.get("running"),
                    scheduler.get("in_flight"),
                    scheduler.get("active"),
                ]
            )
        store = status.get("store")
        if isinstance(store, dict):
            candidates.extend(
                [
                    store.get("queued"),
                    store.get("active"),
                    store.get("pending"),
                ]
            )

        return int(sum(int(value or 0) for value in candidates if isinstance(value, (int, float))))

    @staticmethod
    def _safe_call(fn: Any, default: Any) -> Any:
        try:
            if callable(fn):
                return fn()
        except Exception as exc:
            logger.debug("[telegram] integration call failed: %s", exc)
        return default

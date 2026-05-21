"""Secure Telegram command parser and dispatcher."""

from __future__ import annotations

from typing import Iterable, Optional
from quant_ecosystem.security.security_governor import SecurityGovernor


class CommandHandler:
    """Parses Telegram commands and dispatches to injected system components."""

    def __init__(
        self,
        authorized_users: Optional[Iterable[int | str]] = None,
        autonomous_controller=None,
        strategy_selector=None,
        risk_manager=None,
        system_status_reporter=None,
        capital_allocator_layer=None,
        trading_loop=None,
        router=None, **kwargs
    ):
        self.authorized_users = {str(uid).strip() for uid in (authorized_users or []) if str(uid).strip()}

        self.viewer_users = set(self.authorized_users)
        self.operator_users = {str(uid).strip() for uid in kwargs.get("operator_users", []) if str(uid).strip()}
        self.admin_users = {str(uid).strip() for uid in kwargs.get("admin_users", []) if str(uid).strip()}
        self.break_glass_users = {str(uid).strip() for uid in kwargs.get("break_glass_users", []) if str(uid).strip()}
        self.autonomous_controller = autonomous_controller
        self.strategy_selector = strategy_selector
        self.risk_manager = risk_manager
        self.system_status_reporter = system_status_reporter
        self.capital_allocator_layer = capital_allocator_layer
        self.trading_loop = trading_loop
        self.router = router

    def handle(self, command_text: str, user_id: int | str) -> str:
        if not self.is_authorized(user_id):
            return "Unauthorized user."

        raw = str(command_text or "").strip()

        if not raw:
            return "Empty command."

        if not raw.startswith("/"):
            return "Explicit slash commands only."

        parts = raw[1:].split()
        cmd = parts[0].lower() if parts else ""

        if "@" in cmd:
            cmd = cmd.split("@", 1)[0]

        args = parts[1:]

        if cmd in {"pause", "resume"} and not self.has_operator_access(user_id):
            return "Operator privilege required."

        if cmd in {"emergency_stop", "kill_switch", "live_arm", "live_disarm"} and not self.has_break_glass_access(user_id):
            return "Break-glass privilege required."

        if cmd == "status":
            return self._status()

        if cmd == "system_health":
            return self._system_health()

        if cmd == "pause":
            if not args or args[0] != SecurityGovernor.get_telegram_approval_token():
                return "Approval token required."
            if self.trading_loop:
                return self.trading_loop.stop_loop()
            if self.router:
                try:
                    self.router.stop_trading()
                    self.router.set_auto_mode(False)
                    return "Trading paused."
                except Exception as exc:
                    return f"Pause failed: {exc}"
            return "Router unavailable."

        if cmd == "resume":
            if not args or args[0] != SecurityGovernor.get_telegram_approval_token():
                return "Approval token required."
            if self.trading_loop:
                return self.trading_loop.start_loop()
            if self.router:
                try:
                    self.router.start_trading()
                    self.router.set_auto_mode(True)
                    return "Trading resumed."
                except Exception as exc:
                    return f"Resume failed: {exc}"
            return "Router unavailable."

        if cmd == "activate_strategy":
            return self._activate_strategy(args)

        if cmd == "deactivate_strategy":
            return self._deactivate_strategy(args)

        if cmd == "allocate_capital":
            return self._allocate_capital(args)

        if cmd == "emergency_stop":
            return self._emergency_stop(args)

        if cmd == "kill_switch":
            return self._kill_switch(args)

        if cmd == "live_arm":
            return self._live_arm(args)

        if cmd == "live_disarm":
            return self._live_disarm(args)

        return "Unknown command."

    def _emergency_stop(self, args) -> str:
        if not args or args[0] != SecurityGovernor.get_telegram_approval_token():
            return "Approval token required."

        try:
            if self.router:
                self.router.stop_trading()
                self.router.set_auto_mode(False)
            if self.trading_loop:
                self.trading_loop.stop_loop()
            return "EMERGENCY STOP EXECUTED."
        except Exception as exc:
            return f"Emergency stop failed: {exc}"


    def _kill_switch(self, args) -> str:
        if not args or args[0] != SecurityGovernor.get_telegram_approval_token():
            return "Approval token required."

        try:
            SecurityGovernor.activate_kill_switch()
            if self.router:
                self.router.stop_trading()
                self.router.set_auto_mode(False)
            return "KILL SWITCH ACTIVATED."
        except Exception as exc:
            return f"Kill switch failed: {exc}"


    def _live_arm(self, args) -> str:
        if not args or args[0] != SecurityGovernor.get_telegram_approval_token():
            return "Approval token required."

        return "LIVE ARM acknowledged. Runtime live enable path controlled separately."


    def _live_disarm(self, args) -> str:
        if not args or args[0] != SecurityGovernor.get_telegram_approval_token():
            return "Approval token required."

        try:
            if self.router:
                self.router.set_auto_mode(False)
            return "LIVE DISARMED."
        except Exception as exc:
            return f"Live disarm failed: {exc}"
            
    def is_authorized(self, user_id: int | str) -> bool:
        return self.has_viewer_access(user_id)

    def _uid(self, user_id):
        return str(user_id).strip()

    def has_viewer_access(self, user_id):
        uid = self._uid(user_id)
        return uid in self.viewer_users

    def has_operator_access(self, user_id):
        uid = self._uid(user_id)
        return uid in self.operator_users or uid in self.admin_users or uid in self.break_glass_users

    def has_admin_access(self, user_id):
        uid = self._uid(user_id)
        return uid in self.admin_users or uid in self.break_glass_users

    def has_break_glass_access(self, user_id):
        uid = self._uid(user_id)
        return uid in self.break_glass_users

    def _status(self) -> str:
        reporter = self.system_status_reporter
        if not reporter:
            return "Status reporter unavailable."
        return reporter.status_snapshot()

    def _system_health(self) -> str:
        reporter = self.system_status_reporter
        if not reporter:
            return "Status reporter unavailable."
        return reporter.system_health()

    def _pause(self) -> str:
        return "Pause requires explicit approval token. Use /pause <approval_token>"
        router = self.router
        if not router:
            return "Router unavailable."
        try:
            router.stop_trading()
            router.set_auto_mode(False)
            return "Trading paused."
        except Exception as exc:
            return f"Pause failed: {exc}"

    def _resume(self) -> str:
        return "Resume requires explicit approval token. Use /resume <approval_token>"
        router = self.router
        if not router:
            return "Router unavailable."
        try:
            router.start_trading()
            router.set_auto_mode(True)
            return "Trading resumed."
        except Exception as exc:
            return f"Resume failed: {exc}"

    def _activate_strategy(self, args) -> str:
        if len(args) < 2:
            return "Usage: /activate_strategy <name> <approval_token>"

        name = str(args[0]).strip()
        approval_token = str(args[1]).strip()

        if approval_token != SecurityGovernor.get_telegram_approval_token():
            return "Approval token required."

        selector = self.strategy_selector

        if selector and hasattr(selector, "activation_manager"):
            try:
                return selector.activation_manager.activate_strategy(name)
            except Exception as exc:
                return f"Activation failed: {exc}"

        controller = self.autonomous_controller

        if controller and self.router and hasattr(controller, "deploy_strategy"):
            return controller.deploy_strategy(self.router, name)

        return "Strategy activation path unavailable."
        
    def _deactivate_strategy(self, args) -> str:
        if len(args) < 2:
            return "Usage: /deactivate_strategy <name> <approval_token>"

        name = str(args[0]).strip()
        approval_token = str(args[1]).strip()

        if approval_token != SecurityGovernor.get_telegram_approval_token():
            return "Approval token required."

        selector = self.strategy_selector

        if selector and hasattr(selector, "activation_manager"):
            try:
                return selector.activation_manager.deactivate_strategy(name)
            except Exception as exc:
                return f"Deactivation failed: {exc}"

        return "Strategy deactivation path unavailable."
        
    def _allocate_capital(self, args) -> str:
        if len(args) < 3:
            return "Usage: /allocate_capital <strategy> <amount_pct> <approval_token>"

        strategy = str(args[0]).strip()

        try:
            amount = float(args[1])
        except ValueError:
            return "Invalid amount."

        approval_token = str(args[2]).strip()
        expected = SecurityGovernor.get_telegram_approval_token()

        if approval_token != expected:
            return "Approval token required."

        layer = self.capital_allocator_layer

        if layer and hasattr(layer, "set_manual_allocation"):
            try:
                value = layer.set_manual_allocation(strategy, amount)
                return f"Allocation override set: {strategy}={value}%"
            except Exception as exc:
                return f"Allocation failed: {exc}"

        controller = self.autonomous_controller

        if controller and self.router and hasattr(controller, "allocate"):
            return controller.allocate(self.router, strategy, amount)

        return "Capital allocation path unavailable."

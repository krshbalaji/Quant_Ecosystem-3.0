import requests

from control.telegram_control_center import TelegramControlCenter
from control.telegram.audit_logger import TelegramAuditLogger
from control.telegram.webhook_server import TelegramWebhookServer
from control.telegram.webhook_watchdog import WebhookWatchdog
from core.config_loader import Config


class TelegramController:

    def __init__(self):
        self.config = Config()
        self.token = self.config.telegram_token
        self.chat_id = self.config.telegram_chat_id
        self.router = None
        self._dashboard_message_id = None
        self._current_page = "trading"
        self._webhook_server = None
        self._webhook_enabled = False
        self._polling_fallback = False
        self._update_offset = 0
        self._active_role = "operator"
        self.control_center = TelegramControlCenter()
        self.audit = TelegramAuditLogger(secret=self.config.telegram_audit_secret)
        self.watchdog = WebhookWatchdog(timeout_sec=self.config.telegram_webhook_timeout_sec)

        if not self.token:
            print("Telegram not configured: TELEGRAM_TOKEN missing.")
            return

        self._start_webhook_mode()
        self.set_command_menu()

    def bind_router(self, router):
        self.router = router

    def send_startup_ping(self):
        if not bool(getattr(self.config, "telegram_startup_alert", True)):
            return False
        if not self.token:
            return False
        if not self._is_valid_chat_id(self.chat_id):
            return False
        return self.send_dashboard(role=self._active_role)

    def send_message(self, text):
        if not self._is_valid_chat_id(self.chat_id):
            return False
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": text}
        return self._post(url=url, payload=payload, use_json=True)

    def send_dashboard(self, role="viewer"):
        if not self._is_valid_chat_id(self.chat_id):
            return False
        text = self._dashboard_text()
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "reply_markup": self._inline_keyboard(self._current_page, role),
        }
        ok, data = self._post_raw(url, payload, use_json=True)
        if ok:
            self._dashboard_message_id = data.get("result", {}).get("message_id")
        return ok

    def update_dashboard(self, role=None):
        role = role or self._active_role
        if not self._dashboard_message_id:
            return self.send_dashboard(role=role)

        text = self._dashboard_text()
        url = f"https://api.telegram.org/bot{self.token}/editMessageText"
        payload = {
            "chat_id": self.chat_id,
            "message_id": self._dashboard_message_id,
            "text": text,
            "reply_markup": self._inline_keyboard(self._current_page, role),
        }
        ok = self._post(url=url, payload=payload, use_json=True)
        if not ok:
            return self.send_dashboard(role=role)
        return True

    def set_command_menu(self):
        url = f"https://api.telegram.org/bot{self.token}/setMyCommands"
        payload = {
            "commands": [
                {"command": "dashboard", "description": "Inline control panel"},
                {"command": "status", "description": "System status"},
                {"command": "positions", "description": "Open positions"},
                {"command": "broker", "description": "Broker/source status"},
                {"command": "market_hours", "description": "Market open/closed by prefix"},
                {"command": "pnl", "description": "PnL snapshot"},
                {"command": "strategies", "description": "Active strategies"},
                {"command": "pause", "description": "Pause trading"},
                {"command": "resume", "description": "Resume trading"},
                {"command": "kill", "description": "Emergency stop"},
                {"command": "close_all", "description": "Close all positions"},
                {"command": "report", "description": "Dashboard report"},
                {"command": "metabrain", "description": "Meta strategy decisions"},
                {"command": "cognitive", "description": "Cognitive control snapshot"},
                {"command": "learning", "description": "Adaptive learning snapshot"},
                {"command": "lab_run", "description": "Run one Strategy Lab batch"},
                {"command": "allocate", "description": "Allocate strategy capital"},
                {"command": "deploy_strategy", "description": "Deploy strategy by id"},
                {"command": "manual", "description": "Set MANUAL mode"},
                {"command": "assisted", "description": "Set ASSISTED mode"},
                {"command": "autonomous", "description": "Set AUTONOMOUS mode"},
                {"command": "help", "description": "Show command help"},
            ]
        }
        self._post(url, payload, use_json=True)

    def notify_trade(self, result):
        if result["status"] == "TRADE":
            assist_line = "[LIQUIDATION_ASSIST]\n" if result.get("liquidation_assist") else ""
            if result.get("rebalance_assist"):
                assist_line = "[REBALANCE_ASSIST]\n"
            msg = (
                f"Trade executed\n"
                f"{assist_line}"
                f"{result['strategy_id']} | {result['side']} {result['symbol']} x{result['qty']}\n"
                f"Type: {result.get('trade_type', 'INTRADAY')} | Regime: {result.get('regime', 'NA')}\n"
                f"Price: {result['price']}\n"
                f"Confidence: {result['confidence']}\n"
                f"PnL: {result['pnl']}\n"
                f"Equity: {result['equity']}"
            )
            self.send_message(msg)
            self.update_dashboard(role=self._active_role)
            return

        if result["reason"] in {"NO_SIGNAL", "AUTO_DISABLED"}:
            return
        self.send_message(f"Skipped: {result['reason']}")

    def consume_webhook_events(self):
        updates = []
        if self._webhook_server:
            updates.extend(self._webhook_server.consume())
        if self._polling_fallback:
            updates.extend(self._fetch_polling_updates())

        actions = []
        for item in updates:
            if "callback_query" in item:
                callback = item["callback_query"]
                data = callback.get("data", "")
                chat_id = str(callback.get("message", {}).get("chat", {}).get("id", ""))
                actor_id = str(callback.get("from", {}).get("id", ""))
                print(f"Telegram callback received | actor={actor_id} chat={chat_id} data={data}")
                self._handle_incoming_chat(chat_id)
                if not self._is_chat_allowed(chat_id, actor_id):
                    print(f"Telegram callback rejected | actor={actor_id} chat={chat_id}")
                    continue
                role = self._role_for_actor(actor_id)
                self._active_role = role
                self.watchdog.mark_callback()
                result = self.handle_command(data, actor_id=actor_id)
                self._answer_callback(callback.get("id", ""), result)
                self.update_dashboard(role=role)
                self.audit.log(
                    actor_id=actor_id,
                    role=role,
                    action=data,
                    result=result,
                    page=self._current_page,
                    chat_id=chat_id,
                )
                actions.append((f"button:{data}", result))
                continue

            message = item.get("message", {})
            text = str(message.get("text", "")).strip()
            chat_id = str(message.get("chat", {}).get("id", ""))
            actor_id = str(message.get("from", {}).get("id", ""))
            print(f"Telegram message received | actor={actor_id} chat={chat_id} text={text}")
            self._handle_incoming_chat(chat_id)
            if not self._is_chat_allowed(chat_id, actor_id):
                print(f"Telegram message rejected | actor={actor_id} chat={chat_id}")
                continue
            if text:
                role = self._role_for_actor(actor_id)
                self._active_role = role
                result = self.handle_command(text, actor_id=actor_id)
                if text.lower().lstrip("/") == "dashboard":
                    self.update_dashboard(role=role)
                self.audit.log(
                    actor_id=actor_id,
                    role=role,
                    action=text,
                    result=result,
                    page=self._current_page,
                    chat_id=chat_id,
                )
                actions.append((text, result))

        return actions

    def handle_command(self, command, actor_id=""):
        if not self.router:
            return "Router not attached."

        normalized = command.strip().lower().lstrip("/")
        if "@" in normalized:
            normalized = normalized.split("@", 1)[0]
        role = self._role_for_actor(actor_id)

        if normalized.startswith("page:"):
            self._current_page = normalized.split(":", 1)[1]
            return f"Switched to {self._current_page.title()} page."

        controlled = self.control_center.execute(normalized, self.router)
        if controlled is not None:
            required_role = "viewer"
            if normalized in {"pause", "resume"}:
                required_role = "operator"
            if normalized in {"kill", "close_all"}:
                required_role = "admin"
            if normalized.startswith("lab_run"):
                required_role = "admin"
            if not self._can_execute(role, required_role):
                return f"Denied: {required_role} role required."
            return controlled

        action_map = {
            "status": ("viewer", self.router.get_status_report),
            "positions": ("viewer", self.router.get_positions_report),
            "strategies": ("viewer", self.router.get_strategy_report),
            "dashboard": ("viewer", lambda: "Dashboard refreshed."),
            "refresh": ("viewer", lambda: "Dashboard refreshed."),
            "start": ("operator", self.router.start_trading),
            "stop": ("operator", self.router.stop_trading),
            "auto_on": ("operator", lambda: self.router.set_auto_mode(True)),
            "auto_off": ("operator", lambda: self.router.set_auto_mode(False)),
            "paper": ("operator", lambda: self.router.set_trading_mode("PAPER")),
            "live": ("admin", lambda: self.router.set_trading_mode("LIVE")),
            "25%": ("operator", lambda: self.router.set_risk_preset("25%")),
            "50%": ("operator", lambda: self.router.set_risk_preset("50%")),
            "100%": ("operator", lambda: self.router.set_risk_preset("100%")),
            "alpha": ("operator", lambda: self.router.set_strategy_profile("alpha")),
            "beta": ("operator", lambda: self.router.set_strategy_profile("beta")),
            "gamma": ("operator", lambda: self.router.set_strategy_profile("gamma")),
            "kill": ("admin", self.router.kill_switch),
            "admin_pause": ("admin", self.router.stop_trading),
            "help": ("viewer", lambda: "Use inline pages: Trading, Risk, Strategy, Admin."),
        }

        if normalized not in action_map:
            return "Unknown command. Use /dashboard."

        required_role, fn = action_map[normalized]
        if not self._can_execute(role, required_role):
            return f"Denied: {required_role} role required."
        return fn()

    def _dashboard_text(self):
        if not self.router:
            return "Control panel unavailable."
        return (
            f"{self.router.get_dashboard_report()}\n"
            f"Page: {self._current_page.title()}"
        )

    def _inline_keyboard(self, page, role):
        nav = [
            {"text": "Trading", "callback_data": "page:trading"},
            {"text": "Risk", "callback_data": "page:risk"},
            {"text": "Strategy", "callback_data": "page:strategy"},
        ]
        if role == "admin":
            nav.append({"text": "Admin", "callback_data": "page:admin"})

        rows = [nav]
        if page == "trading":
            rows += [
                [{"text": "Status", "callback_data": "status"}, {"text": "Refresh", "callback_data": "refresh"}],
            ]
            if role in {"operator", "admin"}:
                rows += [
                    [{"text": "Start", "callback_data": "start"}, {"text": "Stop", "callback_data": "stop"}],
                    [{"text": "Auto ON", "callback_data": "auto_on"}, {"text": "Auto OFF", "callback_data": "auto_off"}],
                    [{"text": "PAPER", "callback_data": "paper"}],
                ]
            if role == "admin":
                rows += [
                    [{"text": "LIVE", "callback_data": "live"}],
                ]
        elif page == "risk":
            if role in {"operator", "admin"}:
                rows += [
                    [{"text": "25%", "callback_data": "25%"}, {"text": "50%", "callback_data": "50%"}, {"text": "100%", "callback_data": "100%"}],
                    [{"text": "Status", "callback_data": "status"}],
                ]
            else:
                rows += [
                    [{"text": "Status", "callback_data": "status"}],
                ]
        elif page == "strategy":
            rows += [
                [{"text": "Strategies", "callback_data": "strategies"}, {"text": "Positions", "callback_data": "positions"}],
            ]
            if role in {"operator", "admin"}:
                rows += [
                [{"text": "Alpha", "callback_data": "alpha"}, {"text": "Beta", "callback_data": "beta"}, {"text": "Gamma", "callback_data": "gamma"}],
                ]
        elif page == "admin" and role == "admin":
            rows += [
                [{"text": "Kill", "callback_data": "kill"}, {"text": "Admin Pause", "callback_data": "admin_pause"}],
                [{"text": "Status", "callback_data": "status"}],
            ]
        return {"inline_keyboard": rows}

    def _role_for_actor(self, actor_id):
        actor = str(actor_id).strip()
        if actor and actor in self.config.telegram_admin_ids:
            return "admin"
        if actor and actor in self.config.telegram_operator_ids:
            return "operator"
        if actor and str(self.chat_id) == actor:
            return "operator"
        return "viewer"

    def _can_execute(self, role, required):
        hierarchy = {"viewer": 0, "operator": 1, "admin": 2}
        return hierarchy.get(role, 0) >= hierarchy.get(required, 0)

    def _answer_callback(self, callback_id, text):
        if not callback_id:
            return
        url = f"https://api.telegram.org/bot{self.token}/answerCallbackQuery"
        payload = {"callback_query_id": callback_id, "text": str(text)[:180], "show_alert": False}
        self._post(url, payload, use_json=True)

    def _handle_incoming_chat(self, chat_id):
        if not self._is_valid_chat_id(self.chat_id) and self._is_valid_chat_id(chat_id):
            self.chat_id = chat_id
            self._persist_chat_id(chat_id)
            print(f"Telegram auto-bound chat id: {chat_id}")

    def _is_chat_allowed(self, chat_id, actor_id=""):
        if self._is_valid_chat_id(self.chat_id) and chat_id and str(self.chat_id) != chat_id:
            # Allow trusted actors to rebind chat automatically when they move between chats/devices.
            role = self._role_for_actor(actor_id)
            if role in {"admin", "operator"}:
                self.chat_id = chat_id
                self._persist_chat_id(chat_id)
                print(f"Telegram chat id re-bound by trusted actor: {chat_id}")
                return True
            return False
        return True

    def _start_webhook_mode(self):
        path = self.config.telegram_webhook_path
        if not path.startswith("/"):
            path = "/" + path

        self._webhook_server = TelegramWebhookServer(
            host=self.config.telegram_webhook_host,
            port=self.config.telegram_webhook_port,
            path=path,
            secret_token=self.config.telegram_webhook_secret,
        )
        self._webhook_server.start()

        webhook_url = self.config.telegram_webhook_url
        if not webhook_url:
            self._polling_fallback = True
            print("Telegram webhook URL missing. Running in polling fallback mode.")
            return

        set_url = f"https://api.telegram.org/bot{self.token}/setWebhook"
        payload = {
            "url": webhook_url.rstrip("/") + path,
            "secret_token": self.config.telegram_webhook_secret,
            "drop_pending_updates": True,
        }
        ok = self._post(set_url, payload, use_json=True)
        if ok:
            print(f"Telegram webhook configured: {payload['url']}")
            self._webhook_enabled = True
            self._polling_fallback = False
        else:
            print("Telegram webhook setup failed.")
            self._polling_fallback = True

    def watchdog_tick(self, router):
        if not self._webhook_enabled:
            return None
        if not self.watchdog.should_failover():
            return None

        router.stop_trading()
        router.set_auto_mode(False)
        reason = "WEBHOOK_STALE_FAILOVER_SAFE_MODE"
        self.send_message(f"Safety failover: {reason}")
        return reason

    def _persist_chat_id(self, chat_id):
        try:
            with open(".env", "r", encoding="utf-8") as handle:
                lines = handle.read().splitlines()
        except FileNotFoundError:
            lines = []

        found = False
        updated = []
        for line in lines:
            if line.startswith("TELEGRAM_CHAT_ID="):
                updated.append(f"TELEGRAM_CHAT_ID={chat_id}")
                found = True
            else:
                updated.append(line)

        if not found:
            updated.append(f"TELEGRAM_CHAT_ID={chat_id}")

        with open(".env", "w", encoding="utf-8") as handle:
            handle.write("\n".join(updated).rstrip() + "\n")

    def _is_valid_chat_id(self, chat_id):
        if chat_id is None:
            return False
        value = str(chat_id).strip()
        if not value:
            return False
        if ":" in value:
            return False
        if value.startswith("-"):
            return value[1:].isdigit()
        return value.isdigit()

    def _post(self, url, payload, use_json=False):
        ok, _ = self._post_raw(url, payload, use_json=use_json)
        return ok

    def _post_raw(self, url, payload, use_json=False):
        try:
            response = requests.post(
                url,
                json=payload if use_json else None,
                data=None if use_json else payload,
                timeout=5,
            )
            data = response.json()
            if not data.get("ok"):
                description = str(data.get("description", "unknown error"))
                if "message is not modified" in description.lower():
                    return True, data
                print(f"Telegram API failed: {description}")
                return False, data
            return True, data
        except (requests.RequestException, ValueError):
            print("Telegram API failed: network/API error.")
            return False, {}

    def _fetch_polling_updates(self):
        if not self.token:
            return []
        url = f"https://api.telegram.org/bot{self.token}/getUpdates"
        params = {
            "timeout": 1,
            "offset": self._update_offset + 1,
            "allowed_updates": ["message", "callback_query"],
        }
        try:
            response = requests.get(url, params=params, timeout=3)
            data = response.json()
        except (requests.RequestException, ValueError):
            return []

        if not data.get("ok"):
            return []

        items = data.get("result", [])
        for item in items:
            update_id = int(item.get("update_id", 0))
            if update_id > self._update_offset:
                self._update_offset = update_id
        return items

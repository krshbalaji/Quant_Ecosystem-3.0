import logging
import requests
import time

logger = logging.getLogger(__name__)

from quant_ecosystem.operating.control.telegram_control_center import TelegramControlCenter
from quant_ecosystem.operating.control.telegram.audit_logger import TelegramAuditLogger
from quant_ecosystem.operating.control.telegram.webhook_server import TelegramWebhookServer
from quant_ecosystem.operating.control.telegram.webhook_watchdog import WebhookWatchdog
from quant_ecosystem.operating.core.config_loader import Config


class TelegramController:

    def __init__(self, **kwargs):
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
        
        # Spam prevention
        self._last_alert_time = {}
        self._alert_cooldown = 30  # seconds between similar alerts
        
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

    def send_message(self, text, alert_type=None):
        if not self._is_valid_chat_id(self.chat_id):
            return False
            
        # Spam prevention for alerts
        if alert_type:
            current_time = time.time()
            last_time = self._last_alert_time.get(alert_type, 0)
            if current_time - last_time < self._alert_cooldown:
                print(f"Telegram alert '{alert_type}' suppressed (cooldown)")
                return False
            self._last_alert_time[alert_type] = current_time
        
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            payload = {"chat_id": self.chat_id, "text": text}
            return self._post(url=url, payload=payload, use_json=True)
        except Exception as e:
            logger.warning(f"Telegram send failed: {e}")
            return False

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
                {"command": "start", "description": "🚀 Start the trading system"},
                {"command": "stop", "description": "🛑 Stop trading gracefully"},
                {"command": "pause", "description": "⏸️ Pause trading temporarily"},
                {"command": "resume", "description": "▶️ Resume trading"},
                {"command": "status", "description": "📊 System status overview"},
                {"command": "dashboard", "description": "🎛️ Interactive control panel"},
                {"command": "system", "description": "⚙️ System snapshot"},
                {"command": "positions", "description": "📍 Open positions"},
                {"command": "pnl", "description": "💰 P&L summary"},
                {"command": "strategies", "description": "🧠 Active strategies"},
                {"command": "market_view", "description": "🧠 Market intelligence"},
                {"command": "next_move", "description": "🎯 Suggested next trade"},
                {"command": "help", "description": "❓ Show command help"},
            ]
        }
        self._post(url, payload, use_json=True)

    def notify_trade(self, result):
        if result["status"] == "TRADE":
            assist_line = "[💰 LIQUIDATION_ASSIST]\n" if result.get("liquidation_assist") else ""
            if result.get("rebalance_assist"):
                assist_line = "[🔄 REBALANCE_ASSIST]\n"
            
            symbol = result['symbol']
            side = result['side']
            strategy = result['strategy_id']
            qty = result['qty']
            price = result['price']
            pnl = result['pnl']
            equity = result['equity']
            
            # Format with emojis and clean layout
            msg = (
                f"🚀 *TRADE EXECUTED*\n\n"
                f"{assist_line}"
                f"📈 *Symbol:* {symbol}\n"
                f"{'📈' if side.upper() == 'BUY' else '📉'} *Side:* {side.upper()}\n"
                f"🎯 *Strategy:* {strategy}\n"
                f"📊 *Confidence:* {result['confidence']:.1%}\n"
                f"🌊 *Regime:* {result.get('regime', 'UNKNOWN')}\n"
                f"📦 *Quantity:* {qty} @ ${price:.2f}\n"
                f"💰 *P&L:* ${pnl:.2f} | *Equity:* ${equity:.2f}\n\n"
                f"💭 *Reason:* {result.get('explanation', 'Strategy execution aligned with market conditions.')}"
            )
            self.send_message(msg, alert_type=f"trade_{symbol}")
            self.update_dashboard(role=self._active_role)
            return

        if result["reason"] in {"NO_SIGNAL", "AUTO_DISABLED"}:
            return
            
        # Skip spam for common rejections
        skip_reasons = {"COOLDOWN_ACTIVE", "DAILY_LIMIT_EXCEEDED", "DUPLICATE_CYCLE"}
        if any(reason in result["reason"] for reason in skip_reasons):
            return
            
        self.send_message(f"⚠️ *Trade Skipped:* {result['reason']}", alert_type="skip")

    def send_trade_alert(self, trade):
        if not trade:
            return False
        result = {
            "status": "TRADE",
            "strategy_id": trade.get("strategy", trade.get("strategy_id", "MANUAL")),
            "symbol": trade.get("symbol", "UNKNOWN"),
            "side": trade.get("side", "BUY"),
            "qty": trade.get("qty", 0),
            "trade_type": trade.get("trade_type", "INTRADAY"),
            "regime": trade.get("regime", "NA"),
            "price": trade.get("price", trade.get("entry", 0.0)),
            "confidence": trade.get("confidence", 1.0),
            "pnl": trade.get("pnl", trade.get("realized_pnl", 0.0)),
            "equity": trade.get("equity", 0.0),
            "explanation": trade.get("explanation", ""),
        }
        self.notify_trade(result)
        return True

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
            required_role = self._required_role_for_command(normalized)
            if not self._can_execute(role, required_role):
                return f"Denied: {required_role} role required."
            return controlled

        action_map = {
            "status": ("viewer", self.router.get_status_report),
            "positions": ("viewer", self.router.get_positions_report),
            "strategies": ("viewer", self.router.get_strategy_report),
            "dashboard": ("viewer", lambda: "Dashboard refreshed."),
            "resume": ("operator", self.router.start_trading),
            "restart": ("operator", lambda: "Loop is already continuous; state refreshed."),
            "kill_all": ("admin", self.router.kill_switch),
            "boost_capital": ("operator", lambda: self.router.set_risk_preset("100%")),
            "reduce_risk": ("operator", lambda: self.router.set_risk_preset("25%")),
            "switch_mode": ("operator", lambda: self.router.set_auto_mode(not bool(getattr(self.router.state, "auto_mode", True)))),
            "refresh": ("viewer", lambda: "Dashboard refreshed."),
            "system": ("viewer", lambda: self.control_center.execute("system", self.router)),
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
            "reduce_exposure": ("operator", lambda: self.control_center.execute("reduce_exposure", self.router)),
            "rebalance": ("operator", lambda: self.control_center.execute("rebalance", self.router)),
            "report": ("viewer", self.router.get_dashboard_report),
            "broker": ("viewer", lambda: self.control_center.execute("broker", self.router)),
            "pnl": ("viewer", lambda: self.control_center.execute("pnl", self.router)),
            "why_trade": ("viewer", lambda: self.control_center.execute("why_trade", self.router)),
            "market_view": ("viewer", lambda: self.control_center.execute("market_view", self.router)),
            "next_move": ("viewer", lambda: self.control_center.execute("next_move", self.router)),
            "metabrain": ("viewer", lambda: self.control_center.execute("metabrain", self.router)),
            "cognitive": ("viewer", lambda: self.control_center.execute("cognitive", self.router)),
            "learning": ("viewer", lambda: self.control_center.execute("learning", self.router)),
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
        state = getattr(self.router, "state", None)
        compact = (
            f"{getattr(state, 'trading_mode', 'PAPER')} | "
            f"{round(float(getattr(state, 'equity', 0.0) or 0.0), 2)} | "
            f"{len(getattr(state, 'trade_history', []) or [])} trades | "
            f"{round(float(getattr(state, 'realized_pnl', 0.0) or 0.0), 2)} PnL"
        )
        return (
            f"{compact}\n"
            f"{self.router.get_dashboard_report()}\n"
            f"Page: {self._current_page.title()}"
        )

    def _inline_keyboard(self, page, role):
        nav = [
            {"text": "📊 STATUS", "callback_data": "page:trading"},
            {"text": "💰 PNL", "callback_data": "pnl"},
            {"text": "📍 POSITIONS", "callback_data": "positions"},
            {"text": "⚙️ CONTROL", "callback_data": "page:system"},
            {"text": "🚨 RISK", "callback_data": "page:risk"},
        ]
        if role == "admin":
            nav.append({"text": "🛡 ADMIN", "callback_data": "page:admin"})

        rows = [nav]
        if page == "trading":
            rows += [
                [{"text": "📊 Status", "callback_data": "status"}, {"text": "💰 P&L", "callback_data": "pnl"}, {"text": "📍 Positions", "callback_data": "positions"}],
                [{"text": "🔄 Refresh", "callback_data": "refresh"}, {"text": "📋 Report", "callback_data": "report"}],
                [{"text": "🧠 Market View", "callback_data": "market_view"}, {"text": "🎯 Next Move", "callback_data": "next_move"}],
            ]
            if role in {"operator", "admin"}:
                rows += [
                    [{"text": "▶️ Resume", "callback_data": "resume"}, {"text": "⏸️ Pause", "callback_data": "pause"}],
                    [{"text": "🔄 Rebalance", "callback_data": "rebalance"}, {"text": "⚠️ Reduce Risk", "callback_data": "reduce_exposure"}],
                ]
            if role == "admin":
                rows += [
                    [{"text": "🚨 Emergency Stop", "callback_data": "kill"}],
                ]
        elif page == "risk":
            if role in {"operator", "admin"}:
                rows += [
                    [{"text": "📉 Reduce Risk", "callback_data": "reduce_risk"}, {"text": "⚠️ Reduce Exposure", "callback_data": "reduce_exposure"}],
                    [{"text": "🚨 Emergency", "callback_data": "kill"}],
                ]
            else:
                rows += [
                    [{"text": "📊 Status", "callback_data": "status"}],
                ]
        elif page == "strategy":
            rows += [
                [{"text": "🧠 Strategies", "callback_data": "strategies"}, {"text": "🧬 Meta", "callback_data": "metabrain"}],
                [{"text": "🛰 Cognitive", "callback_data": "cognitive"}, {"text": "📚 Learning", "callback_data": "learning"}],
            ]
            if role in {"operator", "admin"}:
                rows += [
                [{"text": "Alpha", "callback_data": "alpha"}, {"text": "Beta", "callback_data": "beta"}, {"text": "Gamma", "callback_data": "gamma"}],
                ]
        elif page == "system":
            rows += [
                [{"text": "⚙️ System", "callback_data": "system"}, {"text": "🏦 Broker", "callback_data": "broker"}],
                [{"text": "🕒 Market Hours", "callback_data": "market_hours"}, {"text": "❓ Help", "callback_data": "help"}],
            ]
        elif page == "admin" and role == "admin":
            rows += [
                [{"text": "❌ Kill", "callback_data": "kill"}, {"text": "⏸ Admin Pause", "callback_data": "admin_pause"}],
                [{"text": "📦 Close All", "callback_data": "close_all"}, {"text": "🧪 Lab Run", "callback_data": "lab_run"}],
                [{"text": "📊 Status", "callback_data": "status"}],
            ]
        return {"inline_keyboard": rows}

    def _required_role_for_command(self, normalized):
        base = str(normalized or "").split()[0]
        if base in {"status", "system", "positions", "pnl", "strategies", "broker", "market_hours", "report", "metabrain", "cognitive", "learning", "dashboard", "refresh", "help"}:
            return "viewer"
        if base in {
            "pause", "resume", "start", "stop", "auto_on", "auto_off", "paper",
            "25%", "50%", "100%", "alpha", "beta", "gamma", "allocate",
            "deploy_strategy", "activate_strategy", "pause_strategy",
            "manual", "assisted", "autonomous", "reduce_exposure", "rebalance",
            "set_risk", "set_drawdown", "set_multiplier", "execution_mode",
        }:
            return "operator"
        if base in {"kill", "close_all", "admin_pause", "live", "retire_strategy", "lab_run"}:
            return "admin"
        return "viewer"

    def _role_for_actor(self, actor_id):
        actor = str(actor_id).strip()
        if actor and actor in self.config.telegram_admin_ids:
            return "admin"
        if actor and actor in self.config.telegram_operator_ids:
            return "operator"
        if actor and actor in self.config.telegram_viewer_ids:
            return "viewer"
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
                timeout=(5, 15)  # connect timeout, read timeout
            )
            data = response.json()
            if not data.get("ok"):
                description = str(data.get("description", "unknown error"))
                if "message is not modified" in description.lower():
                    return True, data
                print(f"Telegram API failed: {description}")
                return False, data
            return True, data
        except (requests.RequestException, ValueError) as exc:
            logger.warning("Telegram API error: %s", exc)
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
            response = requests.get(url, params=params, timeout=10)
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

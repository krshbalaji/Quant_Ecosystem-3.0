import os

from dotenv import load_dotenv


class Config:

    def __init__(self):
        load_dotenv()

        # Broker
        self.broker_name = os.getenv("BROKER_NAME")
        self.fyers_app_id = os.getenv("FYERS_APP_ID")
        self.fyers_secret = os.getenv("FYERS_SECRET_KEY")
        self.fyers_redirect_uri = os.getenv("FYERS_REDIRECT_URI")
        self.fyers_token = os.getenv("FYERS_ACCESS_TOKEN")

        # Telegram
        self.telegram_token = self._pick_env("TELEGRAM_TOKEN", "TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = self._pick_env("TELEGRAM_CHAT_ID")
        self.telegram_webhook_url = self._pick_env("TELEGRAM_WEBHOOK_URL")
        self.telegram_webhook_secret = self._pick_env("TELEGRAM_WEBHOOK_SECRET")
        self.telegram_webhook_host = os.getenv("TELEGRAM_WEBHOOK_HOST", "127.0.0.1")
        self.telegram_webhook_port = int(os.getenv("TELEGRAM_WEBHOOK_PORT", "8081"))
        self.telegram_webhook_path = os.getenv("TELEGRAM_WEBHOOK_PATH", "/telegram/webhook")
        self.telegram_webhook_timeout_sec = int(os.getenv("TELEGRAM_WEBHOOK_TIMEOUT_SEC", "180"))
        self.telegram_audit_secret = self._pick_env("TELEGRAM_AUDIT_SECRET", "TELEGRAM_WEBHOOK_SECRET")
        self.telegram_admin_ids = self._parse_ids("TELEGRAM_ADMIN_IDS")
        self.telegram_operator_ids = self._parse_ids("TELEGRAM_OPERATOR_IDS")

        # VCS + dependency automation
        self.auto_git_sync = os.getenv("AUTO_GIT_SYNC", "true").lower() == "true"
        self.auto_git_push_end = os.getenv("AUTO_GIT_PUSH_END", "true").lower() == "true"
        self.auto_git_tag_end = os.getenv("AUTO_GIT_TAG_END", "true").lower() == "true"
        self.git_auto_commit_message = os.getenv("GIT_AUTO_COMMIT_MESSAGE", "auto: end-of-session sync")
        include_default = (
            "broker,config,control,core,execution,intelligence,market,portfolio,"
            "reporting,research,risk,strategy_bank,utils,main.py,launcher.py,requests.txt,.gitignore"
        )
        exclude_default = "reporting/output,reporting/output/runtime,reporting/output/audit"
        self.git_sync_paths = self._parse_paths("GIT_SYNC_PATHS", include_default)
        self.git_exclude_paths = self._parse_paths("GIT_EXCLUDE_PATHS", exclude_default)
        self.auto_dependency_install = os.getenv("AUTO_DEP_INSTALL", "true").lower() == "true"
        self.auto_update_probability = float(os.getenv("AUTO_UPDATE_PROBABILITY", "0.25"))

        # Mode
        self.mode = os.getenv("MODE", "PAPER")
        self.auto_start = os.getenv("AUTO_START", "false").lower() == "true"
        symbols = os.getenv("TRADE_SYMBOLS", "NSE:SBIN-EQ,NSE:RELIANCE-EQ,NSE:INFY-EQ")
        self.trade_symbols = [item.strip() for item in symbols.split(",") if item.strip()]

        # Risk
        self.max_daily_loss_pct = min(float(os.getenv("MAX_DAILY_LOSS_PCT", 5)), 5.0)
        self.max_position_pct = min(float(os.getenv("MAX_POSITION_SIZE_PCT", 2)), 2.0)
        self.hard_drawdown_limit_pct = min(float(os.getenv("HARD_DRAWDOWN_LIMIT_PCT", 20)), 20.0)
        self.cooldown_after_loss = int(os.getenv("COOLDOWN_AFTER_LOSS", 3))
        self.max_portfolio_exposure_pct = float(os.getenv("MAX_PORTFOLIO_EXPOSURE_PCT", 40))
        self.max_symbol_exposure_pct = float(os.getenv("MAX_SYMBOL_EXPOSURE_PCT", 20))
        self.max_daily_trades = int(os.getenv("MAX_DAILY_TRADES", "18"))
        self.max_symbol_daily_loss_pct = float(os.getenv("MAX_SYMBOL_DAILY_LOSS_PCT", "1.25"))
        self.max_strategy_capital_pct = min(float(os.getenv("MAX_STRATEGY_CAPITAL_PCT", 30)), 30.0)
        self.max_asset_class_capital_pct = min(float(os.getenv("MAX_ASSET_CLASS_CAPITAL_PCT", 50)), 50.0)
        self.diversification_correlation_threshold = float(os.getenv("DIVERSIFICATION_CORRELATION_THRESHOLD", 0.75))

        # Execution realism
        self.broker_fee_bps = float(os.getenv("BROKER_FEE_BPS", 2.5))
        self.base_slippage_bps = float(os.getenv("BASE_SLIPPAGE_BPS", 1.5))
        self.max_slippage_bps = float(os.getenv("MAX_SLIPPAGE_BPS", 8.0))
        self.capital_cap_multiplier = float(os.getenv("CAPITAL_CAP_MULTIPLIER", 2.0))
        self.allow_paper_shadow = os.getenv("ALLOW_PAPER_SHADOW", "true").lower() == "true"
        self.min_adaptation_trades = int(os.getenv("MIN_ADAPTATION_TRADES", "20"))
        self.min_target_trades = int(os.getenv("MIN_TARGET_TRADES", "20"))
        self.paper_min_profit_factor = float(os.getenv("PAPER_MIN_PROFIT_FACTOR", "1.02"))
        self.paper_min_sharpe = float(os.getenv("PAPER_MIN_SHARPE", "0.0"))
        self.live_min_profit_factor = float(os.getenv("LIVE_MIN_PROFIT_FACTOR", "1.50"))
        self.live_min_sharpe = float(os.getenv("LIVE_MIN_SHARPE", "1.80"))
        self.sizer_min_volatility = float(os.getenv("SIZER_MIN_VOLATILITY", "0.25"))
        self.sizer_max_notional_pct = float(os.getenv("SIZER_MAX_NOTIONAL_PCT", "8.0"))

    def _pick_env(self, *keys):
        placeholders = {"", "your_bot_token", "your_chat_id", "none", "null"}
        for key in keys:
            value = os.getenv(key, "").strip()
            if value.lower() in placeholders:
                continue
            return value
        return ""

    def _parse_ids(self, key):
        raw = os.getenv(key, "").strip()
        if not raw:
            return set()
        ids = set()
        for item in raw.split(","):
            value = item.strip()
            if value.lstrip("-").isdigit():
                ids.add(value)
        return ids

    def _parse_paths(self, key, default):
        raw = os.getenv(key, default).strip()
        if not raw:
            return []
        return [item.strip() for item in raw.split(",") if item.strip()]

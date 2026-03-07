import os

from dotenv import load_dotenv


class Config:

    def __init__(self, **kwargs):
        load_dotenv()

        # Broker
        self.broker_name = os.getenv("BROKER_NAME")
        self.fyers_app_id = os.getenv("FYERS_APP_ID")
        self.fyers_secret = os.getenv("FYERS_SECRET_KEY")
        self.fyers_redirect_uri = os.getenv("FYERS_REDIRECT_URI")
        self.fyers_token = os.getenv("FYERS_ACCESS_TOKEN")
        self.coinswitch_api_key = os.getenv("COINSWITCH_API_KEY", "")
        self.coinswitch_api_secret = os.getenv("COINSWITCH_API_SECRET", "")
        self.coinswitch_base_url = os.getenv("COINSWITCH_BASE_URL", "https://api.coinswitch.co")
        self.coinswitch_enable_live = os.getenv("COINSWITCH_ENABLE_LIVE", "false").lower() == "true"

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
        self.telegram_startup_alert = os.getenv("TELEGRAM_STARTUP_ALERT", "true").lower() == "true"
        self.telegram_always_on = os.getenv("TELEGRAM_ALWAYS_ON", "false").lower() == "true"
        self.telegram_idle_poll_sec = float(os.getenv("TELEGRAM_IDLE_POLL_SEC", "1.0"))

        # VCS + dependency automation
        self.auto_git_sync = os.getenv("AUTO_GIT_SYNC", "true").lower() == "true"
        self.auto_git_push_end = os.getenv("AUTO_GIT_PUSH_END", "true").lower() == "true"
        self.auto_git_tag_end = os.getenv("AUTO_GIT_TAG_END", "true").lower() == "true"
        self.git_auto_commit_message = os.getenv("GIT_AUTO_COMMIT_MESSAGE", "auto: end-of-session sync")
        include_default = (
            "broker,config,control,core,execution,intelligence,market,portfolio,"
            "quant_ecosystem,reporting,research,risk,strategy_bank,utils,main.py,launcher.py,requests.txt,.gitignore"
        )
        exclude_default = "reporting/output,reporting/output/runtime,reporting/output/audit"
        self.git_sync_paths = self._parse_paths("GIT_SYNC_PATHS", include_default)
        self.git_exclude_paths = self._parse_paths("GIT_EXCLUDE_PATHS", exclude_default)
        self.auto_dependency_install = os.getenv("AUTO_DEP_INSTALL", "true").lower() == "true"
        self.auto_update_probability = float(os.getenv("AUTO_UPDATE_PROBABILITY", "0.25"))
        self.intelligence_refresh_cycles = int(os.getenv("INTELLIGENCE_REFRESH_CYCLES", "5"))
        self.enable_global_session_fallback = os.getenv("ENABLE_GLOBAL_SESSION_FALLBACK", "true").lower() == "true"
        self.strict_market_hours = os.getenv("STRICT_MARKET_HOURS", "false").lower() == "true"

        # Institutional strategy bank / mutation flags
        self.enable_strategy_bank = os.getenv("ENABLE_STRATEGY_BANK", "true").lower() == "true"
        self.enable_strategy_mutation = os.getenv("ENABLE_STRATEGY_MUTATION", "false").lower() == "true"
        self.enable_meta_strategy_brain = os.getenv("ENABLE_META_STRATEGY_BRAIN", "false").lower() == "true"
        self.meta_max_active_strategies = int(os.getenv("META_MAX_ACTIVE_STRATEGIES", "5"))
        self.enable_strategy_lab = os.getenv("ENABLE_STRATEGY_LAB", "false").lower() == "true"
        self.strategy_lab_sandbox = os.getenv("STRATEGY_LAB_SANDBOX", "true").lower() == "true"
        self.enable_strategy_lab_autorun = os.getenv("ENABLE_STRATEGY_LAB_AUTORUN", "false").lower() == "true"
        self.strategy_lab_autorun_interval_sec = int(os.getenv("STRATEGY_LAB_AUTORUN_INTERVAL_SEC", "900"))
        self.strategy_lab_autorun_generate_count = int(os.getenv("STRATEGY_LAB_AUTORUN_GENERATE_COUNT", "8"))
        self.strategy_lab_autorun_variants_per_base = int(os.getenv("STRATEGY_LAB_AUTORUN_VARIANTS_PER_BASE", "4"))
        self.strategy_lab_autorun_periods = int(os.getenv("STRATEGY_LAB_AUTORUN_PERIODS", "260"))
        self.enable_alpha_scanner = os.getenv("ENABLE_ALPHA_SCANNER", "false").lower() == "true"
        self.alpha_scanner_interval_sec = int(os.getenv("ALPHA_SCANNER_INTERVAL_SEC", "180"))
        self.alpha_scanner_top_n = int(os.getenv("ALPHA_SCANNER_TOP_N", "100"))
        self.alpha_scanner_max_assets = int(os.getenv("ALPHA_SCANNER_MAX_ASSETS", "1200"))
        self.enable_portfolio_ai = os.getenv("ENABLE_PORTFOLIO_AI", "false").lower() == "true"
        self.portfolio_ai_interval_sec = int(os.getenv("PORTFOLIO_AI_INTERVAL_SEC", "300"))
        self.portfolio_ai_capital_pct = float(os.getenv("PORTFOLIO_AI_CAPITAL_PCT", "100"))
        self.enable_strategy_diversity = os.getenv("ENABLE_STRATEGY_DIVERSITY", "false").lower() == "true"
        self.strategy_diversity_max_per_category = int(os.getenv("STRATEGY_DIVERSITY_MAX_PER_CATEGORY", "3"))
        self.strategy_diversity_max_correlation = float(os.getenv("STRATEGY_DIVERSITY_MAX_CORRELATION", "0.75"))
        self.strategy_diversity_max_per_asset_class = int(os.getenv("STRATEGY_DIVERSITY_MAX_PER_ASSET_CLASS", "4"))
        self.strategy_diversity_max_per_timeframe = int(os.getenv("STRATEGY_DIVERSITY_MAX_PER_TIMEFRAME", "4"))
        self.enable_strategy_survival = os.getenv("ENABLE_STRATEGY_SURVIVAL", "false").lower() == "true"
        self.enable_execution_intelligence = os.getenv("ENABLE_EXECUTION_INTELLIGENCE", "false").lower() == "true"
        self.enable_event_signal_engine = os.getenv("ENABLE_EVENT_SIGNAL_ENGINE", "false").lower() == "true"
        self.event_signal_engine_cooldown_sec = int(os.getenv("EVENT_SIGNAL_ENGINE_COOLDOWN_SEC", "20"))
        self.event_signal_engine_max_immediate_executes = int(os.getenv("EVENT_SIGNAL_ENGINE_MAX_IMMEDIATE_EXECUTES", "3"))
        self.enable_market_pulse_engine = os.getenv("ENABLE_MARKET_PULSE_ENGINE", "false").lower() == "true"
        self.market_pulse_poll_sec = float(os.getenv("MARKET_PULSE_POLL_SEC", "2.0"))
        self.market_pulse_min_strength = float(os.getenv("MARKET_PULSE_MIN_STRENGTH", "0.2"))
        self.enable_event_driven_engine = os.getenv("ENABLE_EVENT_DRIVEN_ENGINE", "false").lower() == "true"
        self.enable_adaptive_learning = os.getenv("ENABLE_ADAPTIVE_LEARNING", "false").lower() == "true"
        self.adaptive_learning_batch_interval_cycles = int(os.getenv("ADAPTIVE_LEARNING_BATCH_INTERVAL_CYCLES", "10"))
        self.enable_cognitive_control = os.getenv("ENABLE_COGNITIVE_CONTROL", "false").lower() == "true"
        self.cognitive_control_interval_sec = float(os.getenv("COGNITIVE_CONTROL_INTERVAL_SEC", "2.0"))
        self.enable_dashboard_server = os.getenv("ENABLE_DASHBOARD_SERVER", "false").lower() == "true"
        self.dashboard_host = os.getenv("DASHBOARD_HOST", "127.0.0.1")
        self.dashboard_port = int(os.getenv("DASHBOARD_PORT", "8090"))
        self.dashboard_update_interval_sec = float(os.getenv("DASHBOARD_UPDATE_INTERVAL_SEC", "0.25"))
        self.enable_cockpit_server = os.getenv("ENABLE_COCKPIT_SERVER", "false").lower() == "true"
        self.cockpit_host = os.getenv("COCKPIT_HOST", "127.0.0.1")
        self.cockpit_port = int(os.getenv("COCKPIT_PORT", "8091"))
        self.cockpit_update_interval_sec = float(os.getenv("COCKPIT_UPDATE_INTERVAL_SEC", "0.25"))
        self.cockpit_auth_token = os.getenv("COCKPIT_AUTH_TOKEN", "")
        self.enable_safety_governor = os.getenv("ENABLE_SAFETY_GOVERNOR", "false").lower() == "true"
        self.safety_governor_interval_sec = float(os.getenv("SAFETY_GOVERNOR_INTERVAL_SEC", "2.0"))
        self.safety_governor_cooldown_sec = float(os.getenv("SAFETY_GOVERNOR_COOLDOWN_SEC", "30.0"))
        self.safety_governor_min_rejection_samples = int(
            os.getenv("SAFETY_GOVERNOR_MIN_REJECTION_SAMPLES", "8")
        )
        self.enable_shadow_trading = os.getenv("ENABLE_SHADOW_TRADING", "false").lower() == "true"
        self.shadow_trading_interval_sec = float(os.getenv("SHADOW_TRADING_INTERVAL_SEC", "2.0"))
        self.shadow_initial_capital = float(os.getenv("SHADOW_INITIAL_CAPITAL", "100000.0"))
        self.enable_alpha_genome_engine = os.getenv("ENABLE_ALPHA_GENOME_ENGINE", "false").lower() == "true"
        self.alpha_genome_interval_sec = float(os.getenv("ALPHA_GENOME_INTERVAL_SEC", "300.0"))
        self.alpha_genome_random_count = int(os.getenv("ALPHA_GENOME_RANDOM_COUNT", "6"))
        self.alpha_genome_mutation_variants = int(os.getenv("ALPHA_GENOME_MUTATION_VARIANTS", "2"))
        self.alpha_genome_cross_children = int(os.getenv("ALPHA_GENOME_CROSS_CHILDREN", "4"))
        self.enable_alpha_factory = os.getenv("ENABLE_ALPHA_FACTORY", "false").lower() == "true"
        self.alpha_factory_generate_every_sec = int(os.getenv("ALPHA_FACTORY_GENERATE_EVERY_SEC", "1800"))
        self.alpha_factory_evaluate_every_sec = int(os.getenv("ALPHA_FACTORY_EVALUATE_EVERY_SEC", "900"))
        self.alpha_factory_max_promotions = int(os.getenv("ALPHA_FACTORY_MAX_PROMOTIONS", "3"))
        self.enable_global_market_brain = os.getenv("ENABLE_GLOBAL_MARKET_BRAIN", "false").lower() == "true"
        self.global_market_brain_interval_sec = float(os.getenv("GLOBAL_MARKET_BRAIN_INTERVAL_SEC", "120.0"))
        self.global_market_brain_telegram_events = os.getenv("GLOBAL_MARKET_BRAIN_TELEGRAM_EVENTS", "true").lower() == "true"
        self.global_market_brain_dashboard_events = os.getenv("GLOBAL_MARKET_BRAIN_DASHBOARD_EVENTS", "true").lower() == "true"
        self.enable_microstructure_simulation = os.getenv("ENABLE_MICROSTRUCTURE_SIMULATION", "false").lower() == "true"
        self.microstructure_base_delay_ms = float(os.getenv("MICROSTRUCTURE_BASE_DELAY_MS", "120"))
        self.microstructure_spread_multiplier = float(os.getenv("MICROSTRUCTURE_SPREAD_MULTIPLIER", "1.0"))
        self.microstructure_slippage_multiplier = float(os.getenv("MICROSTRUCTURE_SLIPPAGE_MULTIPLIER", "1.0"))
        self.enable_regime_ai = os.getenv("ENABLE_REGIME_AI", "false").lower() == "true"
        self.regime_ai_model_path = os.getenv("REGIME_AI_MODEL_PATH", "quant_ecosystem/regime_ai/models/regime_model.pkl")
        self.regime_ai_min_confidence = float(os.getenv("REGIME_AI_MIN_CONFIDENCE", "0.45"))
        self.correlation_threshold = float(os.getenv("CORRELATION_THRESHOLD", "0.7"))
        self.min_trades_for_promotion = int(os.getenv("MIN_TRADES_FOR_PROMOTION", "100"))
        self.mutation_rate_per_day = int(os.getenv("MUTATION_RATE_PER_DAY", "2"))
        self.mutation_batch_size = int(os.getenv("MUTATION_BATCH_SIZE", "8"))
        self.mutation_min_sharpe = float(os.getenv("MUTATION_MIN_SHARPE", "1.2"))
        self.mutation_min_profit_factor = float(os.getenv("MUTATION_MIN_PROFIT_FACTOR", "1.3"))
        self.mutation_max_drawdown = float(os.getenv("MUTATION_MAX_DRAWDOWN", "15"))
        self.mutation_max_capital_exposure_pct = float(os.getenv("MUTATION_MAX_CAPITAL_EXPOSURE_PCT", "30"))

        # Mode
        self.mode = os.getenv("MODE", "PAPER")
        self.operation_mode = os.getenv("OPERATION_MODE", "AUTONOMOUS")
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
        self.max_sector_exposure_pct = float(os.getenv("MAX_SECTOR_EXPOSURE_PCT", 35))
        self.max_strategy_exposure_pct = float(os.getenv("MAX_STRATEGY_EXPOSURE_PCT", 30))
        self.max_asset_exposure_pct = float(os.getenv("MAX_ASSET_EXPOSURE_PCT", 50))
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
        self.liquidation_assist_enabled = os.getenv("LIQUIDATION_ASSIST_ENABLED", "true").lower() == "true"
        self.liquidation_assist_trigger_streak = int(os.getenv("LIQUIDATION_ASSIST_TRIGGER_STREAK", "4"))
        self.liquidation_assist_close_fraction = float(os.getenv("LIQUIDATION_ASSIST_CLOSE_FRACTION", "0.25"))

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


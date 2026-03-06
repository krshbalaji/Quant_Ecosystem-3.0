from quant_ecosystem.core.config_loader import Config


class RiskEngine:

    def __init__(self, config=None):
        """
        Optionally accept an explicit Config instance for consistency with
        SystemFactory wiring while remaining backward compatible with
        no-argument construction in existing tests and helpers.
        """
        config = config or Config()
        self.max_daily_dd = config.max_daily_loss_pct
        self.hard_drawdown_limit = config.hard_drawdown_limit_pct
        self.max_trade_risk = config.max_position_pct
        self.base_trade_risk = config.max_position_pct
        self.min_trade_risk = max(0.25, config.max_position_pct * 0.25)
        self.max_trade_risk_cap = min(2.0, max(config.max_position_pct, 2.0))
        self.max_portfolio_risk = config.max_portfolio_exposure_pct
        self.max_symbol_risk = config.max_symbol_exposure_pct
        self.max_daily_trades = max(1, config.max_daily_trades)
        self.max_symbol_daily_loss_pct = max(0.1, config.max_symbol_daily_loss_pct)
        self.max_sector_exposure_pct = config.max_sector_exposure_pct
        self.max_strategy_exposure_pct = config.max_strategy_exposure_pct
        self.max_asset_exposure_pct = config.max_asset_exposure_pct
        self.cooldown_after_loss = config.cooldown_after_loss

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def allow_trade(
        self,
        state,
        portfolio_exposure_pct=0.0,
        symbol_exposure_pct=0.0,
        daily_trade_count=0,
        symbol_daily_loss_pct=0.0,
        sector_exposure_pct=0.0,
        strategy_exposure_pct=0.0,
        asset_exposure_pct=0.0,
        exposure_reducing=False,
        active_strategy_count=1,
    ):
        if state.trading_halted:
            return False, "TRADING_HALTED"

        if state.total_drawdown_pct >= self.hard_drawdown_limit:
            state.trading_halted = True
            return False, "HARD_DD_LIMIT"

        if state.daily_drawdown >= self.max_daily_dd:
            state.trading_halted = True
            state.trading_enabled = False
            return False, "MAX_DAILY_LOSS"

        if state.total_drawdown_pct > self.max_daily_dd:
            state.trading_halted = True
            return False, "MAX_DD_HALT"

        if state.cooldown > 0:
            return False, "COOLDOWN"

        if int(daily_trade_count) >= self.max_daily_trades:
            return False, "MAX_DAILY_TRADES"

        if float(symbol_daily_loss_pct) >= self.max_symbol_daily_loss_pct:
            return False, "MAX_SYMBOL_DAILY_LOSS"

        if (not exposure_reducing) and float(sector_exposure_pct) >= self.max_sector_exposure_pct:
            return False, "MAX_SECTOR_EXPOSURE"

        if (
            (not exposure_reducing)
            and int(active_strategy_count) > 1
            and float(strategy_exposure_pct) >= self.max_strategy_exposure_pct
        ):
            return False, "MAX_STRATEGY_EXPOSURE"

        if (not exposure_reducing) and float(asset_exposure_pct) >= self.max_asset_exposure_pct:
            return False, "MAX_ASSET_EXPOSURE"

        if (not exposure_reducing) and portfolio_exposure_pct >= self.max_portfolio_risk:
            return False, "MAX_PORTFOLIO_EXPOSURE"

        if (not exposure_reducing) and symbol_exposure_pct >= self.max_symbol_risk:
            return False, "MAX_SYMBOL_EXPOSURE"

        return True, "OK"

    # Backwards compatible alias expected by some callers.
    def check_trade(
        self,
        state,
        portfolio_exposure_pct=0.0,
        symbol_exposure_pct=0.0,
        daily_trade_count=0,
        symbol_daily_loss_pct=0.0,
        sector_exposure_pct=0.0,
        strategy_exposure_pct=0.0,
        asset_exposure_pct=0.0,
        exposure_reducing=False,
        active_strategy_count=1,
    ):
        return self.allow_trade(
            state=state,
            portfolio_exposure_pct=portfolio_exposure_pct,
            symbol_exposure_pct=symbol_exposure_pct,
            daily_trade_count=daily_trade_count,
            symbol_daily_loss_pct=symbol_daily_loss_pct,
            sector_exposure_pct=sector_exposure_pct,
            strategy_exposure_pct=strategy_exposure_pct,
            asset_exposure_pct=asset_exposure_pct,
            exposure_reducing=exposure_reducing,
            active_strategy_count=active_strategy_count,
        )

    def trade_risk(self, equity):
        return equity * (self.max_trade_risk / 100.0)

    def set_trade_risk_pct(self, value):
        self.max_trade_risk = max(self.min_trade_risk, min(value, self.max_trade_risk_cap))
        return self.max_trade_risk

    def calculate_position_size(self, equity, price, volatility=None):
        """
        Simple position sizing helper based on configured per-trade risk.
        """
        if price <= 0:
            return 0
        risk_budget = self.trade_risk(equity)
        return max(int(risk_budget / float(price)), 0)

    def update_risk(self, performance=None):
        """
        Placeholder hook for dynamic risk adjustment.
        Currently a no-op to keep the interface stable.
        """
        return {
            "max_trade_risk": self.max_trade_risk,
            "max_portfolio_risk": self.max_portfolio_risk,
        }

from core.config_loader import Config


class RiskEngine:

    def __init__(self):
        config = Config()
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

        if float(sector_exposure_pct) >= self.max_sector_exposure_pct:
            return False, "MAX_SECTOR_EXPOSURE"

        if float(strategy_exposure_pct) >= self.max_strategy_exposure_pct:
            return False, "MAX_STRATEGY_EXPOSURE"

        if float(asset_exposure_pct) >= self.max_asset_exposure_pct:
            return False, "MAX_ASSET_EXPOSURE"

        if portfolio_exposure_pct >= self.max_portfolio_risk:
            return False, "MAX_PORTFOLIO_EXPOSURE"

        if symbol_exposure_pct >= self.max_symbol_risk:
            return False, "MAX_SYMBOL_EXPOSURE"

        return True, "OK"

    def trade_risk(self, equity):
        return equity * (self.max_trade_risk / 100.0)

    def set_trade_risk_pct(self, value):
        self.max_trade_risk = max(self.min_trade_risk, min(value, self.max_trade_risk_cap))
        return self.max_trade_risk

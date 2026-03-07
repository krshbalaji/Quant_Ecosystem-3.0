from quant_ecosystem.utils.decimal_utils import quantize


class SystemState:

    def __init__(self, **kwargs):
        self.initial_equity = 100000.0
        self.cash_balance = 100000.0
        self.equity = 100000.0
        self.peak_equity = 100000.0
        self.day_start_equity = 100000.0
        self.capital_cap = 200000.0

        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.fees_paid = 0.0
        self.turnover = 0.0

        self.daily_drawdown = 0.0
        self.total_drawdown_pct = 0.0

        self.consecutive_losses = 0
        self.cooldown = 0

        self.open_positions = 0
        self.trade_history = []
        self.latest_prices = {}
        self.trading_enabled = True
        self.trading_halted = False
        self.auto_mode = True
        self.trading_mode = "PAPER"
        self.strategy_profile = "BETA"
        self.risk_preset = "100%"
        self.account_source = "SIMULATED"
        self.last_reconciled_at = None
        self.broker_orders_count = 0
        self.broker_trades_count = 0
        self.broker_positions_count = 0

    def apply_fill_accounting(self, side, fill_notional, fee, realized_pnl):
        if side == "BUY":
            self.cash_balance -= fill_notional + fee
        else:
            self.cash_balance += fill_notional - fee

        self.cash_balance = quantize(self.cash_balance, 4)
        self.fees_paid = quantize(self.fees_paid + fee, 4)
        self.turnover = quantize(self.turnover + fill_notional, 4)
        self.realized_pnl = quantize(self.realized_pnl + realized_pnl, 4)

    def mark_to_market(self, portfolio_engine):
        self.unrealized_pnl = portfolio_engine.unrealized_pnl(self.latest_prices)
        portfolio_value = portfolio_engine.market_value(self.latest_prices)
        self.equity = quantize(self.cash_balance + portfolio_value, 4)
        if self.equity > self.capital_cap:
            self.equity = quantize(self.capital_cap, 4)
            self.trading_enabled = False

        if self.equity > self.peak_equity:
            self.peak_equity = self.equity

        if self.peak_equity > 0:
            dd = ((self.peak_equity - self.equity) / self.peak_equity) * 100.0
        else:
            dd = 0.0
        self.total_drawdown_pct = quantize(dd, 4)
        if self.day_start_equity > 0:
            daily_dd = ((self.day_start_equity - self.equity) / self.day_start_equity) * 100.0
        else:
            daily_dd = 0.0
        self.daily_drawdown = quantize(max(daily_dd, 0.0), 4)

    def update_loss_streak(self, cycle_pnl_abs):
        if cycle_pnl_abs < 0:
            self.consecutive_losses += 1
            if self.consecutive_losses >= 3:
                self.cooldown = 3
        else:
            self.consecutive_losses = 0
            if self.cooldown > 0:
                self.cooldown -= 1

    def reset_daily(self):
        self.day_start_equity = self.equity
        self.daily_drawdown = 0.0
        self.consecutive_losses = 0
        self.cooldown = 0

    def record_trade(self, trade):
        self.trade_history.append(trade)

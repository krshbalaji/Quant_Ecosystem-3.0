from datetime import datetime

from quant_ecosystem.utils.decimal_utils import quantize


class BrokerReconciler:

    def __init__(self, broker_router, portfolio_engine, state, **kwargs):
        self.broker = broker_router
        self.portfolio = portfolio_engine
        self.state = state

    def reconcile(self, latest_prices):
        snapshot = self.broker.get_account_snapshot(latest_prices=latest_prices)
        self.portfolio.replace_positions(snapshot.get("positions", []))

        self.state.cash_balance = quantize(snapshot.get("cash_balance", self.state.cash_balance), 4)
        self.state.realized_pnl = quantize(snapshot.get("realized_pnl", self.state.realized_pnl), 4)
        self.state.unrealized_pnl = quantize(snapshot.get("unrealized_pnl", self.state.unrealized_pnl), 4)
        self.state.fees_paid = quantize(snapshot.get("fees_paid", self.state.fees_paid), 4)
        self.state.equity = quantize(snapshot.get("equity", self.state.equity), 4)
        self.state.open_positions = self.portfolio.exposure()
        self.state.account_source = str(snapshot.get("account_source", "SIMULATED"))
        self.state.last_reconciled_at = datetime.now().isoformat(timespec="seconds")
        self.state.broker_orders_count = int(len(snapshot.get("orders", [])))
        self.state.broker_trades_count = int(len(snapshot.get("tradebook", [])))
        self.state.broker_positions_count = int(len(snapshot.get("positions", [])))

        if self.state.equity > self.state.peak_equity:
            self.state.peak_equity = self.state.equity
        if self.state.peak_equity > 0:
            drawdown = ((self.state.peak_equity - self.state.equity) / self.state.peak_equity) * 100.0
        else:
            drawdown = 0.0
        self.state.total_drawdown_pct = quantize(drawdown, 4)
        if self.state.day_start_equity > 0:
            daily_dd = ((self.state.day_start_equity - self.state.equity) / self.state.day_start_equity) * 100.0
        else:
            daily_dd = 0.0
        self.state.daily_drawdown = quantize(max(daily_dd, 0.0), 4)

        return snapshot

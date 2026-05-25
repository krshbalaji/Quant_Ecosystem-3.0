class BacktestEngine:

    def simulate_fill(
        self,
        event,
    ):
        return {
            "symbol": event["symbol"],
            "side": event["side"],
            "qty": event["qty"],
            "fill_price": float(
                event["price"]
            ),
        }

    def pnl_for_trade(
        self,
        entry,
        exit_event,
    ):
        side = entry["side"]

        entry_price = float(
            entry["fill_price"]
        )

        exit_price = float(
            exit_event["price"]
        )

        qty = int(entry["qty"])

        if side == "BUY":
            pnl = (
                exit_price - entry_price
            ) * qty
        else:
            pnl = (
                entry_price - exit_price
            ) * qty

        return pnl

    def equity_curve(
        self,
        pnl_series,
        starting_equity=100000,
    ):
        curve = [starting_equity]

        current = starting_equity

        for pnl in pnl_series:
            current += pnl
            curve.append(current)

        return curve

    def run(
        self,
        trade_pairs,
        starting_equity=100000,
    ):
        pnls = []
        trades = []

        for pair in trade_pairs:
            entry = self.simulate_fill(
                pair["entry"]
            )

            pnl = self.pnl_for_trade(
                entry,
                pair["exit"],
            )

            pnls.append(pnl)

            trades.append(
                {
                    "symbol": entry["symbol"],
                    "pnl": pnl,
                }
            )

        curve = self.equity_curve(
            pnls,
            starting_equity,
        )

        wins = len(
            [
                x for x in pnls
                if x > 0
            ]
        )

        losses = len(
            [
                x for x in pnls
                if x <= 0
            ]
        )

        return {
            "trades": trades,
            "pnls": pnls,
            "equity_curve": curve,
            "wins": wins,
            "losses": losses,
            "total_pnl": sum(pnls),
        }


backtest_engine = BacktestEngine()
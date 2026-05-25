class CostEngine:

    def apply_slippage(
        self,
        price,
        side,
        slippage_bps=5,
    ):
        adjustment = (
            price * slippage_bps
        ) / 10000.0

        if side == "BUY":
            return price + adjustment

        return price - adjustment

    def commission(
        self,
        turnover,
        commission_bps=2,
    ):
        return (
            turnover * commission_bps
        ) / 10000.0

    def net_trade_pnl(
        self,
        entry_price,
        exit_price,
        qty,
        side,
        slippage_bps=5,
        commission_bps=2,
    ):
        entry_exec = self.apply_slippage(
            entry_price,
            side,
            slippage_bps,
        )

        exit_side = (
            "SELL"
            if side == "BUY"
            else "BUY"
        )

        exit_exec = self.apply_slippage(
            exit_price,
            exit_side,
            slippage_bps,
        )

        if side == "BUY":
            gross = (
                exit_exec - entry_exec
            ) * qty
        else:
            gross = (
                entry_exec - exit_exec
            ) * qty

        turnover = (
            (
                entry_exec
                + exit_exec
            )
            * qty
        )

        fees = self.commission(
            turnover,
            commission_bps,
        )

        return {
            "gross_pnl": gross,
            "fees": fees,
            "net_pnl": gross - fees,
        }


cost_engine = CostEngine()
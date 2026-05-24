"""
QE3 PnL Engine
Pack23
"""


class PnLEngine:
    def compute_unrealized(
        self,
        snapshot,
        market_price: float,
    ):
        market_price = float(market_price)

        unrealized = 0.0

        for lot in snapshot.open_lots:
            pnl = (
                market_price - float(lot.entry_price)
            ) * int(lot.qty)

            unrealized += pnl

        snapshot.unrealized_pnl = unrealized
        snapshot.gross_pnl = (
            snapshot.realized_pnl + snapshot.unrealized_pnl
        )

        snapshot.net_pnl = (
            snapshot.gross_pnl
            - snapshot.total_fees
            - snapshot.total_slippage
        )

        return snapshot

    def weighted_avg_entry(self, snapshot):
        total_qty = 0
        total_cost = 0.0

        for lot in snapshot.open_lots:
            qty = int(lot.qty)
            total_qty += qty
            total_cost += qty * float(lot.entry_price)

        if total_qty <= 0:
            return 0.0

        return total_cost / total_qty


pnl_engine = PnLEngine()
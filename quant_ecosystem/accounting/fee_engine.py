"""
QE3 Fee Engine
Pack23
"""


class FeeEngine:
    def apply_costs(
        self,
        snapshot,
        fees=0.0,
        slippage=0.0,
    ):
        fees = float(fees)
        slippage = float(slippage)

        snapshot.total_fees += fees
        snapshot.total_slippage += slippage

        snapshot.net_pnl = (
            snapshot.gross_pnl
            - snapshot.total_fees
            - snapshot.total_slippage
        )

        return snapshot

    def estimate_flat_fee(
        self,
        qty,
        flat_rate=0.0,
    ):
        return float(qty) * float(flat_rate)


fee_engine = FeeEngine()
"""
QE3 Master Accounting Engine
Pack23
"""

from quant_ecosystem.accounting.trade_models import (
    AccountingMethod,
)

from quant_ecosystem.accounting.accounting_registry import (
    accounting_registry,
)

from quant_ecosystem.accounting.lot_matcher import (
    lot_matcher,
)

from quant_ecosystem.accounting.fee_engine import (
    fee_engine,
)

from quant_ecosystem.accounting.pnl_engine import (
    pnl_engine,
)


class AccountingEngine:
    def process_fill(
        self,
        fill,
        method=AccountingMethod.FIFO,
    ):
        if accounting_registry.fill_seen(fill.fill_id):
            return accounting_registry.get_snapshot(fill.symbol)

        snapshot = accounting_registry.get_snapshot(fill.symbol)

        lot_matcher.apply_fill(
            snapshot=snapshot,
            fill=fill,
            method=method,
        )

        fee_engine.apply_costs(
            snapshot=snapshot,
            fees=fill.fees,
            slippage=fill.slippage,
        )

        accounting_registry.mark_fill_seen(fill.fill_id)

        return snapshot

    def mark_to_market(
        self,
        symbol: str,
        market_price: float,
    ):
        snapshot = accounting_registry.get_snapshot(symbol)

        pnl_engine.compute_unrealized(
            snapshot=snapshot,
            market_price=market_price,
        )

        return snapshot

    def weighted_avg_entry(
        self,
        symbol: str,
    ):
        snapshot = accounting_registry.get_snapshot(symbol)

        return pnl_engine.weighted_avg_entry(snapshot)

    def clear(self):
        accounting_registry.clear()


accounting_engine = AccountingEngine()
"""
QE3 Master Accounting Engine
Pack23 + Pack25 Instrument Master Integration
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

from quant_ecosystem.instruments import instrument_resolver


class AccountingEngine:

    def _resolve_instrument(self, symbol):
        try:
            return instrument_resolver.resolve(symbol)
        except Exception:
            return None

    def _instrument_multiplier(self, instrument):
        if not instrument:
            return 1.0

        multiplier = getattr(instrument, "multiplier", None)

        if multiplier is None:
            multiplier = getattr(
                instrument,
                "contract_multiplier",
                1.0,
            )

        try:
            return float(multiplier or 1.0)
        except Exception:
            return 1.0

    def _normalize_fill(self, fill):
        """
        Pack25:
        Convert derivative fills into multiplier-aware accounting semantics
        while preserving existing FIFO/LIFO engines.
        """

        instrument = self._resolve_instrument(fill.symbol)
        multiplier = self._instrument_multiplier(instrument)

        try:
            fill.multiplier = multiplier
        except Exception:
            pass

        try:
            fill.notional = (
                float(fill.qty)
                * float(fill.price)
                * multiplier
            )
        except Exception:
            pass

        return fill

    def process_fill(
        self,
        fill,
        method=AccountingMethod.FIFO,
    ):
        fill = self._normalize_fill(fill)

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

        multiplier = getattr(snapshot, "multiplier", 1.0)

        adjusted_market = (
            float(market_price)
            * float(multiplier)
        )

        pnl_engine.compute_unrealized(
            snapshot=snapshot,
            market_price=adjusted_market,
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
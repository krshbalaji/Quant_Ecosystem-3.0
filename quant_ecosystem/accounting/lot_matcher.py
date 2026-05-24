"""
QE3 Lot Matching Engine
Pack23
"""

from quant_ecosystem.accounting.trade_models import (
    AccountingMethod,
    CanonicalTaxLot,
)


class LotMatcher:
    def _select_lots(self, lots, method):
        if method == AccountingMethod.FIFO:
            return lots

        elif method == AccountingMethod.LIFO:
            return list(reversed(lots))

        raise ValueError(f"unsupported lot method: {method}")

    def apply_fill(self, snapshot, fill, method=AccountingMethod.FIFO):
        """
        BUY:
            opens inventory lots

        SELL:
            matches lots and realizes pnl
        """

        if fill.side.upper() == "BUY":
            snapshot.open_lots.append(
                CanonicalTaxLot(
                    symbol=fill.symbol,
                    qty=fill.qty,
                    entry_price=fill.price,
                    broker=fill.broker,
                )
            )
            snapshot.fills_processed += 1
            return snapshot

        if fill.side.upper() != "SELL":
            raise ValueError("unsupported side")

        remaining = fill.qty
        realized = 0.0

        selected = self._select_lots(snapshot.open_lots, method)

        consumed = []

        for lot in selected:
            if remaining <= 0:
                break

            matched = min(remaining, lot.qty)

            pnl = (fill.price - lot.entry_price) * matched
            realized += pnl

            lot.qty -= matched
            remaining -= matched

            if lot.qty <= 0:
                consumed.append(lot)

        for lot in consumed:
            if lot in snapshot.open_lots:
                snapshot.open_lots.remove(lot)

        if remaining > 0:
            raise ValueError("sell exceeds available inventory")

        snapshot.realized_pnl += realized
        snapshot.gross_pnl += realized
        snapshot.fills_processed += 1

        return snapshot


lot_matcher = LotMatcher()
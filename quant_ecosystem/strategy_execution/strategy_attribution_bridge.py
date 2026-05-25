from quant_ecosystem.strategy_execution import (
    strategy_execution_context,
)


class StrategyAttributionBridge:

    def __init__(self):
        self._ledger = {}

    def clear(self):
        self._ledger.clear()

    def _ensure_strategy(
        self,
        strategy_id,
    ):
        if strategy_id not in self._ledger:
            self._ledger[strategy_id] = {
                "realized_pnl": 0.0,
                "unrealized_pnl": 0.0,
                "trade_count": 0,
                "wins": 0,
                "losses": 0,
            }

        return self._ledger[strategy_id]

    def record_fill(
        self,
        order_id,
        pnl=0.0,
    ):
        ctx = strategy_execution_context.get(
            order_id
        )

        if not ctx:
            return None

        strategy_id = ctx["strategy_id"]

        bucket = self._ensure_strategy(
            strategy_id
        )

        pnl = float(pnl)

        bucket["trade_count"] += 1
        bucket["realized_pnl"] += pnl

        if pnl > 0:
            bucket["wins"] += 1
        elif pnl < 0:
            bucket["losses"] += 1

        return bucket

    def mark_unrealized(
        self,
        strategy_id,
        pnl,
    ):
        bucket = self._ensure_strategy(
            strategy_id
        )

        bucket["unrealized_pnl"] = float(pnl)

        return bucket

    def summary(
        self,
        strategy_id,
    ):
        bucket = self._ledger.get(
            strategy_id
        )

        if not bucket:
            return None

        total = bucket["wins"] + bucket["losses"]

        win_rate = (
            (bucket["wins"] / total) * 100.0
            if total > 0 else 0.0
        )

        return {
            **bucket,
            "total_pnl": (
                bucket["realized_pnl"]
                + bucket["unrealized_pnl"]
            ),
            "win_rate": win_rate,
        }

    def all_summaries(self):
        return {
            k: self.summary(k)
            for k in self._ledger
        }


strategy_attribution_bridge = (
    StrategyAttributionBridge()
)
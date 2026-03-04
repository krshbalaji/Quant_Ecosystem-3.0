"""Market microstructure simulator.

Simulates spread, slippage, partial fills, order book depth impact, and
execution delay, then returns a simulated execution price.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from quant_ecosystem.microstructure.liquidity_model import LiquidityModel
from quant_ecosystem.microstructure.slippage_model import SlippageModel
from quant_ecosystem.microstructure.spread_model import SpreadModel


class MicrostructureSimulator:
    """Execution realism helper for lab/backtests/execution intelligence."""

    def __init__(
        self,
        liquidity_model: Optional[LiquidityModel] = None,
        spread_model: Optional[SpreadModel] = None,
        slippage_model: Optional[SlippageModel] = None,
        base_delay_ms: float = 120.0,
    ):
        self.liquidity_model = liquidity_model or LiquidityModel()
        self.spread_model = spread_model or SpreadModel()
        self.slippage_model = slippage_model or SlippageModel()
        self.base_delay_ms = max(1.0, float(base_delay_ms))

    def simulate_execution(
        self,
        symbol: str,
        side: str,
        quantity: float,
        reference_price: float,
        asset_class: str = "stocks",
        volatility: float = 0.2,
        volume: float = 100000.0,
        market_depth: float = 50000.0,
        trade_flow: float = 25000.0,
        timestamp: datetime | None = None,
    ) -> Dict:
        """Simulate an execution and return execution price + fill details."""
        qty = max(0.0, float(quantity))
        ref = max(1e-9, float(reference_price))
        side_u = str(side or "BUY").upper()

        liq = self.liquidity_model.estimate(volume=volume, market_depth=market_depth, trade_flow=trade_flow)
        spread = self.spread_model.estimate(
            volatility=volatility,
            asset_class=asset_class,
            timestamp=timestamp,
        )
        slip = self.slippage_model.estimate(
            volatility=volatility,
            order_size=qty,
            liquidity_score=liq["liquidity_score"],
        )

        spread_amt = ref * float(spread["spread_pct"])
        slip_amt = ref * float(slip["slippage_pct"])

        # Partial fill probability under low liquidity + large size.
        fill_ratio = min(1.0, max(0.2, liq["liquidity_score"] * (1.0 / (1.0 + qty / 300.0)) * 1.8))
        filled_qty = max(0.0, round(qty * fill_ratio, 6))
        unfilled_qty = max(0.0, round(qty - filled_qty, 6))

        if side_u == "BUY":
            executed_price = ref + (spread_amt / 2.0) + slip_amt
        else:
            executed_price = ref - (spread_amt / 2.0) - slip_amt

        # Delay expands with slippage + poor liquidity.
        delay_ms = self.base_delay_ms * (1.0 + (slip["liquidity_penalty"] - 1.0) * 0.5 + slip["size_factor"] * 0.08)
        delay_ms = min(3000.0, max(self.base_delay_ms, delay_ms))

        return {
            "symbol": str(symbol),
            "side": side_u,
            "reference_price": round(ref, 8),
            "simulated_execution_price": round(executed_price, 8),
            "requested_qty": qty,
            "filled_qty": filled_qty,
            "unfilled_qty": unfilled_qty,
            "fill_ratio": round(fill_ratio, 6),
            "execution_delay_ms": round(delay_ms, 3),
            "spread_pct": spread["spread_pct"],
            "slippage_pct": slip["slippage_pct"],
            "liquidity_score": liq["liquidity_score"],
            "components": {
                "spread": spread,
                "slippage": slip,
                "liquidity": liq,
            },
        }

    def apply_to_backtest_metrics(
        self,
        metrics: Dict,
        asset_class: str = "stocks",
        average_order_size: float = 10.0,
        average_volatility: float = 0.2,
        average_volume: float = 150000.0,
        average_depth: float = 80000.0,
    ) -> Dict:
        """Applies microstructure penalties to backtest metrics."""
        out = dict(metrics or {})
        liq = self.liquidity_model.estimate(
            volume=average_volume,
            market_depth=average_depth,
            trade_flow=average_volume * 0.2,
        )
        spread = self.spread_model.estimate(
            volatility=average_volatility,
            asset_class=asset_class,
        )
        slip = self.slippage_model.estimate(
            volatility=average_volatility,
            order_size=average_order_size,
            liquidity_score=liq["liquidity_score"],
        )

        cost_penalty = float(spread["spread_pct"]) + float(slip["slippage_pct"])

        returns: List[float] = []
        for item in out.get("returns", []) or []:
            try:
                returns.append(float(item) - cost_penalty)
            except (TypeError, ValueError):
                continue
        if returns:
            out["returns"] = returns

        out["expectancy"] = float(out.get("expectancy", 0.0)) - (cost_penalty * 100.0)
        out["profit_factor"] = max(0.0, float(out.get("profit_factor", 0.0)) * (1.0 - min(0.35, cost_penalty * 30.0)))
        out["sharpe"] = float(out.get("sharpe", 0.0)) - (cost_penalty * 20.0)
        out["microstructure_penalty_pct"] = round(cost_penalty, 8)
        out["liquidity_score"] = liq["liquidity_score"]
        out["simulated_cost_components"] = {
            "spread_pct": spread["spread_pct"],
            "slippage_pct": slip["slippage_pct"],
        }
        return out


"""Execution Intelligence Brain."""

from __future__ import annotations

from typing import Dict, Optional

from quant_ecosystem.execution_intelligence.execution_policy_manager import (
    ExecutionPolicyManager,
)
from quant_ecosystem.execution_intelligence.liquidity_analyzer import LiquidityAnalyzer
from quant_ecosystem.execution_intelligence.order_optimizer import OrderOptimizer
from quant_ecosystem.execution_intelligence.slippage_estimator import SlippageEstimator


class ExecutionBrain:
    """Optimizes execution decisions before orders hit broker layer."""

    def __init__(
        self,
        liquidity_analyzer: Optional[LiquidityAnalyzer] = None,
        slippage_estimator: Optional[SlippageEstimator] = None,
        order_optimizer: Optional[OrderOptimizer] = None,
        policy_manager: Optional[ExecutionPolicyManager] = None,
        microstructure_simulator=None,
    ):
        self.liquidity_analyzer = liquidity_analyzer or LiquidityAnalyzer()
        self.slippage_estimator = slippage_estimator or SlippageEstimator()
        self.order_optimizer = order_optimizer or OrderOptimizer()
        self.policy_manager = policy_manager or ExecutionPolicyManager()
        self.microstructure_simulator = microstructure_simulator

    def build_instruction(
        self,
        symbol: str,
        side: str,
        quantity: int,
        strategy_signal: Dict | None = None,
        market_context: Dict | None = None,
    ) -> Dict:
        """Return optimized execution instruction."""
        signal = strategy_signal or {}
        context = market_context or {}

        spread = float(context.get("spread", 0.05))
        volatility = float(context.get("volatility", 0.5))
        volume = float(context.get("volume", 10000.0))
        depth = float(context.get("depth", context.get("bid_ask_depth", 5000.0)))
        activity = float(context.get("recent_trade_activity", volume / 10.0))
        regime = str(context.get("market_regime", signal.get("regime", "RANGE_BOUND"))).upper()
        urgency = float(signal.get("urgency", signal.get("confidence", 0.5)))

        liq = self.liquidity_analyzer.analyze(
            volume=volume,
            bid_ask_depth=depth,
            recent_trade_activity=activity,
        )
        slip = self.slippage_estimator.estimate(
            spread=spread,
            volatility=volatility,
            order_size=quantity,
            liquidity_depth=max(1.0, depth),
        )
        policy = self.policy_manager.select_policy(
            market_regime=regime,
            liquidity_score=liq["liquidity_score"],
            urgency=urgency,
            expected_slippage=slip["expected_slippage"],
        )
        opt = self.order_optimizer.optimize(
            symbol=symbol,
            side=side,
            quantity=quantity,
            spread=spread,
            liquidity_score=liq["liquidity_score"],
            expected_slippage=slip["expected_slippage"],
            execution_policy=policy["execution_policy"],
        )

        sim_execution = None
        if self.microstructure_simulator:
            ref_price = float(context.get("last_price", context.get("mid_price", signal.get("reference_price", 100.0))))
            sim_execution = self.microstructure_simulator.simulate_execution(
                symbol=symbol,
                side=side,
                quantity=quantity,
                reference_price=ref_price,
                asset_class=str(context.get("asset_class", "stocks")),
                volatility=volatility,
                volume=volume,
                market_depth=depth,
                trade_flow=activity,
            )

        payload = {
            "symbol": opt["symbol"],
            "side": opt["side"],
            "order_type": opt["order_type"],
            "quantity": opt["quantity"],
            "slice_count": opt["slice_count"],
            "expected_slippage": opt["expected_slippage"],
            "execution_policy": opt["execution_policy"],
            "slices": opt.get("slices", []),
            "liquidity_score": liq["liquidity_score"],
            "slippage_components": slip["components"],
        }
        if sim_execution:
            payload["simulated_execution"] = sim_execution
            payload["simulated_execution_price"] = sim_execution.get("simulated_execution_price")
        return payload

    def execute(self, router, instruction: Dict) -> Dict:
        """Dispatch instruction through existing router/broker interfaces."""
        symbol = str(instruction.get("symbol", ""))
        side = str(instruction.get("side", "BUY")).upper()
        qty = int(max(0, int(instruction.get("quantity", 0))))
        slices = list(instruction.get("slices", []))
        if qty <= 0 or not symbol:
            return {"ok": False, "reason": "INVALID_INSTRUCTION"}

        # Prefer broker router place_order if available.
        broker = getattr(router, "broker", None)
        if broker and hasattr(broker, "place_order"):
            placed = []
            try:
                if slices:
                    for item in slices:
                        sq = int(max(0, int(item.get("quantity", 0))))
                        if sq <= 0:
                            continue
                        placed.append(broker.place_order(symbol=symbol, side=side, qty=sq))
                else:
                    placed.append(broker.place_order(symbol=symbol, side=side, qty=qty))
                return {"ok": True, "placed": len(placed), "broker_responses": placed}
            except Exception as exc:
                return {"ok": False, "reason": str(exc)}

        # Fallback: if router has helper.
        if hasattr(router, "place_order"):
            try:
                if slices:
                    for item in slices:
                        sq = int(max(0, int(item.get("quantity", 0))))
                        if sq > 0:
                            router.place_order(symbol=symbol, side=side, qty=sq)
                else:
                    router.place_order(symbol=symbol, side=side, qty=qty)
                return {"ok": True, "placed": len(slices) if slices else 1}
            except Exception as exc:
                return {"ok": False, "reason": str(exc)}

        return {"ok": False, "reason": "NO_EXECUTION_INTERFACE"}

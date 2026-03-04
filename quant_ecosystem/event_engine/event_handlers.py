"""Event handlers for event-driven trading actions."""

from __future__ import annotations

import asyncio
from typing import Dict, Optional


class EventHandlers:
    """Handler set that triggers module actions by event type."""

    def __init__(
        self,
        router=None,
        strategy_selector=None,
        alpha_scanner=None,
        strategy_lab_controller=None,
        execution_engine=None,
        meta_strategy_brain=None,
    ):
        self.router = router
        self.strategy_selector = strategy_selector
        self.alpha_scanner = alpha_scanner
        self.strategy_lab_controller = strategy_lab_controller
        self.execution_engine = execution_engine
        self.meta_strategy_brain = meta_strategy_brain

    async def dispatch(self, handler_name: str, event: Dict) -> Dict:
        fn = getattr(self, handler_name, None)
        if fn is None:
            return {"ok": False, "handler": handler_name, "reason": "HANDLER_NOT_FOUND"}
        try:
            out = fn(event)
            if asyncio.iscoroutine(out):
                out = await out
            return {"ok": True, "handler": handler_name, "result": out}
        except Exception as exc:
            return {"ok": False, "handler": handler_name, "reason": str(exc)}

    async def handle_volatility_spike(self, event: Dict) -> Dict:
        out = {"event_type": "VOLATILITY_SPIKE", "triggered": []}
        if self.strategy_selector is not None:
            out["triggered"].append("strategy_selector")
            setattr(self.strategy_selector, "last_event", event)
        if self.meta_strategy_brain is not None:
            out["triggered"].append("meta_strategy_brain")
            setattr(self.meta_strategy_brain, "last_event", event)
        return out

    async def handle_breakout(self, event: Dict) -> Dict:
        out = {"event_type": str(event.get("event_type", "PRICE_BREAKOUT")), "triggered": []}
        if self.alpha_scanner is not None and hasattr(self.alpha_scanner, "scan_once"):
            try:
                await self.alpha_scanner.scan_once(top_n=20)
                out["triggered"].append("alpha_scanner")
            except Exception:
                pass

        # Optional immediate signal->execution reaction.
        if self.router is not None and getattr(self.router, "strategy_engine", None):
            snapshot = dict(event.get("snapshot", event.get("details", {}).get("snapshot", {})) or {})
            if snapshot:
                snapshots = [snapshot]
                try:
                    signals = self.router.strategy_engine.evaluate(
                        snapshots,
                        market_bias="NEUTRAL",
                        regime=str(getattr(self.router.autonomous_controller, "last_regime", "MEAN_REVERSION")).upper()
                        if getattr(self.router, "autonomous_controller", None)
                        else "MEAN_REVERSION",
                    )
                except Exception:
                    signals = []
                if signals and hasattr(self.router, "execute"):
                    lock = getattr(self.router, "execution_lock", None)
                    if lock:
                        async with lock:
                            await self.router.execute(signal=signals[0], market_bias="NEUTRAL", regime="MEAN_REVERSION")
                    else:
                        await self.router.execute(signal=signals[0], market_bias="NEUTRAL", regime="MEAN_REVERSION")
                    out["triggered"].append("execution_engine")
        return out

    async def handle_volume_event(self, event: Dict) -> Dict:
        out = {"event_type": "VOLUME_SPIKE", "triggered": []}
        if self.strategy_lab_controller is not None and hasattr(self.strategy_lab_controller, "run_experiment"):
            # Small batch to keep event handling lightweight.
            result = self.strategy_lab_controller.run_experiment(
                generate_count=2,
                variants_per_base=2,
                periods=180,
            )
            out["triggered"].append("strategy_lab")
            out["result"] = {
                "validated": len(result.get("VALIDATED_STRATEGIES", [])),
                "promoted": len(result.get("PROMOTED_STRATEGIES", [])),
                "sandbox": bool(result.get("sandbox_mode", True)),
            }
        return out

    async def handle_liquidity_drop(self, event: Dict) -> Dict:
        out = {"event_type": "LIQUIDITY_DROP", "triggered": []}
        if self.execution_engine is not None:
            setattr(self.execution_engine, "last_event", event)
            out["triggered"].append("execution_engine")
        if self.meta_strategy_brain is not None:
            setattr(self.meta_strategy_brain, "last_event", event)
            out["triggered"].append("meta_strategy_brain")
        return out


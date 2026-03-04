"""Event-driven signal orchestration engine.

Triggers immediate signal evaluation when critical market events occur.
"""

from __future__ import annotations

import asyncio
import time
from typing import Dict, Iterable, List, Optional

from quant_ecosystem.event_signal_engine.event_detector import MarketEventDetector


class EventDrivenSignalEngine:
    """Event-driven trigger layer for scanner + strategy signal evaluation."""

    def __init__(
        self,
        event_detector: Optional[MarketEventDetector] = None,
        event_cooldown_sec: int = 20,
        max_immediate_executes: int = 3,
        enabled_event_types: Optional[Iterable[str]] = None,
    ):
        self.event_detector = event_detector or MarketEventDetector()
        self.event_cooldown_sec = max(1, int(event_cooldown_sec))
        self.max_immediate_executes = max(0, int(max_immediate_executes))
        self.enabled_event_types = set(
            enabled_event_types
            or {
                "volatility_spike",
                "volume_spike",
                "price_breakout_up",
                "price_breakout_down",
                "order_flow_imbalance_buy_pressure",
                "order_flow_imbalance_sell_pressure",
            }
        )
        self._last_trigger_ts: Dict[str, float] = {}
        self.last_events: List[Dict] = []
        self.last_results: Dict = {}

    async def process_snapshots(
        self,
        snapshots: Iterable[Dict],
        router=None,
        alpha_scanner=None,
        market_bias: str = "NEUTRAL",
        regime: str = "MEAN_REVERSION",
        scanner_top_n: int = 20,
    ) -> Dict:
        """Ingest snapshots and trigger immediate evaluation on events."""
        events = []
        for snap in snapshots:
            events.extend(self.event_detector.ingest_snapshot(snap))

        # Filter by enabled types and cooldown.
        triggered = []
        for ev in events:
            if ev["event_type"] not in self.enabled_event_types:
                continue
            key = f"{ev['symbol']}|{ev['event_type']}"
            now = time.time()
            prev = self._last_trigger_ts.get(key, 0.0)
            if (now - prev) < self.event_cooldown_sec:
                continue
            self._last_trigger_ts[key] = now
            triggered.append(ev)

        self.last_events = triggered
        if not triggered:
            result = {"events": [], "scanner_triggered": False, "strategy_signals": [], "executed": []}
            self.last_results = result
            return result

        scanner_result = await self._trigger_alpha_scanner(alpha_scanner, top_n=scanner_top_n)
        strategy_signals = self._trigger_strategy_signals(
            router=router,
            snapshots=snapshots,
            market_bias=market_bias,
            regime=regime,
        )
        executed = await self._trigger_execution(router=router, strategy_signals=strategy_signals, market_bias=market_bias, regime=regime)

        result = {
            "events": triggered,
            "scanner_triggered": bool(scanner_result.get("triggered", False)),
            "scanner_result": scanner_result,
            "strategy_signals": strategy_signals,
            "executed": executed,
        }
        self.last_results = result
        return result

    async def _trigger_alpha_scanner(self, alpha_scanner, top_n: int) -> Dict:
        if alpha_scanner is None or not hasattr(alpha_scanner, "scan_once"):
            return {"triggered": False, "reason": "SCANNER_UNAVAILABLE"}
        try:
            rows = await alpha_scanner.scan_once(top_n=max(5, int(top_n)))
            return {"triggered": True, "opportunities": len(rows)}
        except Exception as exc:
            return {"triggered": False, "reason": str(exc)}

    def _trigger_strategy_signals(self, router, snapshots: Iterable[Dict], market_bias: str, regime: str) -> List[Dict]:
        if router is None or not getattr(router, "strategy_engine", None):
            return []
        try:
            signals = router.strategy_engine.evaluate(list(snapshots), market_bias=market_bias, regime=regime)
            # Expose for downstream modules.
            setattr(router, "last_event_driven_signals", list(signals))
            return list(signals)
        except Exception:
            return []

    async def _trigger_execution(self, router, strategy_signals: List[Dict], market_bias: str, regime: str) -> List[Dict]:
        if router is None or not strategy_signals or self.max_immediate_executes <= 0:
            return []
        out = []
        limit = min(len(strategy_signals), self.max_immediate_executes)
        for sig in strategy_signals[:limit]:
            try:
                # Immediate execution path: bypass wait for next global cycle.
                if hasattr(router, "execute"):
                    res = await router.execute(signal=sig, market_bias=market_bias, regime=regime)
                    out.append(res)
                elif hasattr(router, "run_cycle"):
                    res = router.run_cycle(signal=sig, market_bias=market_bias, regime=regime)
                    out.append(res)
            except Exception as exc:
                out.append({"status": "SKIP", "reason": str(exc), "symbol": sig.get("symbol")})
        return out

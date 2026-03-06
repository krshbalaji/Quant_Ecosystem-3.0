"""Global Alpha Scanner core orchestration."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Dict, Iterable, List, Optional

from quant_ecosystem.alpha_scanner.market_data_adapter import MarketDataAdapter
from quant_ecosystem.alpha_scanner.opportunity_ranker import OpportunityRanker
from quant_ecosystem.alpha_scanner.signal_detector import SignalDetector
from quant_ecosystem.alpha_scanner.universe_manager import UniverseManager


class GlobalAlphaScanner:
    """Asynchronous, scalable alpha scanner for multi-asset universes."""

    def __init__(
        self,
        strategy_lab_controller=None,
        strategy_bank_layer=None,
        meta_strategy_brain=None,
        market_data_adapter: Optional[MarketDataAdapter] = None,
        universe_manager: Optional[UniverseManager] = None,
        signal_detector: Optional[SignalDetector] = None,
        opportunity_ranker: Optional[OpportunityRanker] = None,
        cycle_interval_sec: int = 60,
        max_assets_per_cycle: int = 1200,
    ):
        self.strategy_lab_controller = strategy_lab_controller
        self.strategy_bank_layer = strategy_bank_layer
        self.meta_strategy_brain = meta_strategy_brain
        self.market_data_adapter = market_data_adapter or MarketDataAdapter()
        self.universe_manager = universe_manager or UniverseManager()
        self.signal_detector = signal_detector or SignalDetector()
        self.opportunity_ranker = opportunity_ranker or OpportunityRanker()
        self.cycle_interval_sec = max(30, int(cycle_interval_sec))
        self.max_assets_per_cycle = max(100, int(max_assets_per_cycle))
        self._running = False
        self._latest: List[Dict] = []

    async def scan_once(
        self,
        groups: Iterable[str] | None = None,
        top_n: int = 100,
        lookback: int = 80,
    ) -> List[Dict]:
        """Run one full scan cycle and publish top opportunities."""
        universe = self.universe_manager.load_universe(groups=groups)
        universe = self.universe_manager.filter_by_liquidity(universe, min_liquidity_score=0.25)
        universe = universe[: self.max_assets_per_cycle]
        snapshots = await self.market_data_adapter.fetch_many(universe, lookback=lookback)
        filtered = self.universe_manager.filter_by_volatility(snapshots, min_volatility=0.005, max_volatility=15.0)

        opportunities: List[Dict] = []
        for snapshot in filtered:
            opportunities.extend(self.signal_detector.detect(snapshot))

        ranked = self.opportunity_ranker.rank(opportunities, top_n=top_n)
        self._latest = ranked
        self._publish(ranked)
        return ranked

    async def run_forever(
        self,
        groups: Iterable[str] | None = None,
        top_n: int = 100,
        lookback: int = 80,
    ) -> None:
        """Continuously scan in 1-5 minute intervals (configured interval)."""
        self._running = True
        while self._running:
            try:
                await self.scan_once(groups=groups, top_n=top_n, lookback=lookback)
            except Exception:
                pass
            await asyncio.sleep(self.cycle_interval_sec)

    def stop(self) -> None:
        self._running = False

    def latest_opportunities(self) -> List[Dict]:
        return list(self._latest)

    def _publish(self, opportunities: List[Dict]) -> None:
        if not opportunities:
            return
        payload = {
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "count": len(opportunities),
            "opportunities": opportunities,
        }

        # Strategy Lab hook: store opportunities as research feed metadata.
        lab = self.strategy_lab_controller
        if lab and hasattr(lab, "repository"):
            try:
                rows = []
                for item in opportunities[:50]:
                    sid = f"alpha_{item['symbol'].replace(':', '_')}_{item['signal_type']}"
                    rows.append(
                        {
                            "id": sid,
                            "name": sid,
                            "strategy_type": item.get("signal_type", "scanner_signal"),
                            "category": "scanner_signal",
                            "family": "scanner_signal",
                            "asset_class": item.get("asset_class", "stocks"),
                            "timeframe": item.get("timeframe", "5m"),
                            "entry_logic": item.get("signal_type", "signal_entry"),
                            "exit_logic": "signal_decay_exit",
                            "indicators": [],
                            "parameters": {"signal_strength": float(item.get("signal_strength", 0.0))},
                            "stage": "RESEARCH",
                            "active": False,
                            "metadata": {
                                "mutation_origin": "global_alpha_scanner",
                                "scanner_score": float(item.get("score", 0.0)),
                                "symbol": item.get("symbol"),
                            },
                        }
                    )
                lab.repository.save_research(rows)
            except Exception:
                pass

        # Strategy Bank hook: update lightweight opportunity snapshot.
        layer = self.strategy_bank_layer
        if layer and hasattr(layer, "is_enabled") and layer.is_enabled():
            try:
                registry = layer.bank_engine.registry
                registry.upsert(
                    {
                        "id": "alpha_scanner_feed",
                        "name": "alpha_scanner_feed",
                        "asset_class": "multi",
                        "timeframe": "multi",
                        "category": "scanner",
                        "regime_preference": ["TRENDING", "RANGING", "HIGH_VOL", "LOW_VOL", "CRASH"],
                        "sharpe": 0.0,
                        "profit_factor": 0.0,
                        "max_drawdown": 0.0,
                        "win_rate": 0.0,
                        "expectancy": 0.0,
                        "active": False,
                        "allocation_pct": 0.0,
                        "correlation_cluster": "scanner_feed",
                        "stage": "RESEARCH",
                        "non_deployable": True,
                        "score": float(len(opportunities)),
                        "sample_size": int(len(opportunities)),
                        "returns": [],
                        "scanner_payload": payload,
                    }
                )
                registry.save()
            except Exception:
                pass

        # Meta brain hook: allow immediate evaluation of promoted scanner ideas.
        brain = self.meta_strategy_brain
        if brain:
            try:
                candidates = []
                for item in opportunities[:20]:
                    sid = f"scan_{item['symbol'].replace(':', '_')}_{item['signal_type']}"
                    candidates.append(
                        {
                            "id": sid,
                            "category": "scanner_signal",
                            "family": "scanner_signal",
                            "asset_class": item.get("asset_class", "stocks"),
                            "timeframe": item.get("timeframe", "5m"),
                            "stage": "RESEARCH",
                            "metrics": {
                                "sharpe": float(item.get("score", 0.0)),
                                "profit_factor": 1.0 + float(item.get("signal_strength", 0.0)),
                                "max_dd": max(0.0, 25.0 - float(item.get("score", 0.0)) * 10.0),
                                "win_rate": float(item.get("signal_strength", 0.0)) * 100.0,
                                "expectancy": float(item.get("score", 0.0)) - 0.5,
                                "sample_size": 30,
                                "returns": [],
                            },
                        }
                    )
                brain.promote_new_strategies(candidates)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# SystemFactory-compatible alias
# ---------------------------------------------------------------------------

class AlphaScannerCore:
    """Minimal SystemFactory entry-point for the alpha scanner.

    Delegates to :class:`GlobalAlphaScanner` when available.
    """

    def __init__(self) -> None:
        import logging as _logging
        self._log = _logging.getLogger(__name__)
        self._delegate = None
        try:
            self._delegate = GlobalAlphaScanner()
        except Exception as exc:  # noqa: BLE001
            self._log.warning("AlphaScannerCore: delegate unavailable (%s) — stub mode", exc)
        self._log.info("AlphaScannerCore initialized")

    def scan(self, universe: list | None = None, regime: str = "UNKNOWN") -> list:
        """Scan *universe* for alpha opportunities in *regime*.

        Returns a list of opportunity dicts; returns ``[]`` on error.
        """
        if self._delegate is not None:
            try:
                import asyncio as _asyncio
                loop = _asyncio.new_event_loop()
                try:
                    return loop.run_until_complete(
                        self._delegate.scan_universe(symbols=universe or [], regime=regime)
                    ) or []
                finally:
                    loop.close()
            except Exception as exc:  # noqa: BLE001
                self._log.warning("AlphaScannerCore.scan: delegate error (%s)", exc)
        return []

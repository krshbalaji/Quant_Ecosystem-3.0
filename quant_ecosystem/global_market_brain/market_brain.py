"""Global Market Brain orchestrator."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, Optional

from quant_ecosystem.global_market_brain.cross_asset_analyzer import CrossAssetAnalyzer
from quant_ecosystem.global_market_brain.liquidity_monitor import LiquidityMonitor
from quant_ecosystem.global_market_brain.macro_signal_engine import MacroSignalEngine
from quant_ecosystem.global_market_brain.regime_classifier import GlobalRegimeClassifier


class GlobalMarketBrain:
    """Collects cross-asset data, classifies macro regime, and publishes guidance."""

    def __init__(
        self,
        cross_asset_analyzer: Optional[CrossAssetAnalyzer] = None,
        regime_classifier: Optional[GlobalRegimeClassifier] = None,
        liquidity_monitor: Optional[LiquidityMonitor] = None,
        macro_signal_engine: Optional[MacroSignalEngine] = None,
    ):
        self.cross_asset_analyzer = cross_asset_analyzer or CrossAssetAnalyzer()
        self.regime_classifier = regime_classifier or GlobalRegimeClassifier()
        self.liquidity_monitor = liquidity_monitor or LiquidityMonitor()
        self.macro_signal_engine = macro_signal_engine or MacroSignalEngine()
        self.last_output: Dict = {}

    def analyze(self, snapshots: Iterable[Dict], macro_inputs: Dict | None = None) -> Dict:
        cross_asset = self.cross_asset_analyzer.analyze(snapshots)
        liquidity = self.liquidity_monitor.evaluate(snapshots=snapshots, macro_inputs=macro_inputs)
        regime_row = self.regime_classifier.classify(
            cross_asset=cross_asset,
            liquidity=liquidity,
            macro_inputs=macro_inputs,
        )
        macro_signals = self.macro_signal_engine.generate(regime_row, cross_asset, liquidity)
        output = {
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "regime": regime_row.get("regime"),
            "volatility_state": regime_row.get("volatility_state"),
            "liquidity_state": regime_row.get("liquidity_state"),
            "preferred_strategy_type": regime_row.get("preferred_strategy_type"),
            "macro_signals": macro_signals,
            "cross_asset": cross_asset,
            "liquidity": liquidity,
        }
        self.last_output = output
        return output

    def publish(
        self,
        output: Dict,
        market_pulse_engine=None,
        meta_strategy_brain=None,
        portfolio_ai=None,
        alpha_factory=None,
        adaptive_learning_engine=None,
    ) -> Dict:
        published = {}
        targets = {
            "market_pulse_engine": market_pulse_engine,
            "meta_strategy_brain": meta_strategy_brain,
            "portfolio_ai": portfolio_ai,
            "alpha_factory": alpha_factory,
            "adaptive_learning_engine": adaptive_learning_engine,
        }
        for name, target in targets.items():
            if target is None:
                continue
            try:
                setattr(target, "global_market_brain_signal", output)
                published[name] = True
            except Exception:
                published[name] = False
        return {"published": published, "count": len(published)}


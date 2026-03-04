from quant_ecosystem.core.config_loader import Config


class LiveStrategyEngine:

    def __init__(self, strategy_registry):
        self.strategy_registry = strategy_registry
        self.strategies = strategy_registry.load()
        self.active_ids = None
        self.stage_by_id = {}
        self.shadow_ids = set()
        self.config = Config()
        self.fallback_id = "core_trend_follow_v1"
        if self.strategies:
            self.fallback_id = self.strategies[0]["id"]

    def reload(self):
        self.strategies = self.strategy_registry.load()
        self.active_ids = None
        self.stage_by_id = {}
        self.shadow_ids = set()
        if self.strategies:
            self.fallback_id = self.strategies[0]["id"]
        return self.strategies

    def apply_policy(self, strategy_reports):
        approved = {
            report["id"]
            for report in strategy_reports
            if report.get("stage") in {"PAPER", "LIVE", "PAPER_SHADOW"}
        }
        self.active_ids = approved
        self.stage_by_id = {report["id"]: report.get("stage", "REJECTED") for report in strategy_reports}
        self.shadow_ids = {
            report["id"]
            for report in strategy_reports
            if report.get("stage") == "PAPER_SHADOW"
        }

    def evaluate(self, snapshots, market_bias="NEUTRAL", regime="MEAN_REVERSION"):
        signals = []
        for snapshot in snapshots:
            symbol = snapshot["symbol"]
            side, confidence, strategy_id = self._evaluate_single(snapshot, market_bias, regime)
            if side == "HOLD":
                continue

            signals.append(
                {
                    "strategy_id": strategy_id,
                    "strategy_stage": self.stage_by_id.get(strategy_id, "UNKNOWN"),
                    "shadow_mode": strategy_id in self.shadow_ids,
                    "symbol": symbol,
                    "side": side,
                    "price": snapshot["price"],
                    "confidence": confidence,
                    "volatility": snapshot["volatility"],
                    "trend": snapshot["trend"],
                    "candle_angle": snapshot.get("candle_angle", 0.0),
                    "candle_patterns": snapshot.get("candle_patterns", []),
                }
            )
        return signals

    def _evaluate_single(self, snapshot, market_bias, regime):
        closes = snapshot["close"]
        trend = snapshot["trend"]
        volatility = snapshot["volatility"]

        best = ("HOLD", 0.0, self.fallback_id)
        for strategy in self.strategies:
            if self.active_ids is not None and strategy["id"] not in self.active_ids:
                continue
            if regime not in strategy.get("supported_regimes", []):
                continue

            try:
                decision = strategy["callable"]({"close": closes})
            except Exception:
                continue

            if decision not in {"BUY", "SELL"}:
                continue

            confidence = self._confidence_from_context(
                decision=decision,
                trend=trend,
                volatility=volatility,
                market_bias=market_bias,
            )
            if confidence > best[1]:
                best = (decision, confidence, strategy["id"])

        if best[0] == "HOLD":
            best = self._fallback_signal(trend=trend, volatility=volatility, market_bias=market_bias)

        return best

    def _fallback_signal(self, trend, volatility, market_bias):
        if self.active_ids is not None and self.fallback_id not in self.active_ids:
            return "HOLD", 0.0, self.fallback_id

        if market_bias == "RISK_OFF":
            return "HOLD", 0.0, self.fallback_id

        if trend > 0 and market_bias != "SHORT_BIAS":
            return "BUY", self._confidence_from_context("BUY", trend, volatility, market_bias), self.fallback_id
        if trend < 0 and market_bias != "LONG_BIAS":
            return "SELL", self._confidence_from_context("SELL", trend, volatility, market_bias), self.fallback_id
        return "HOLD", 0.0, self.fallback_id

    def _confidence_from_context(self, decision, trend, volatility, market_bias):
        confidence = 0.55

        if decision == "BUY" and trend > 0:
            confidence += 0.15
        if decision == "SELL" and trend < 0:
            confidence += 0.15

        if volatility < 1.0:
            confidence += 0.05
        if volatility > 2.5:
            confidence -= 0.1

        if market_bias == "LONG_BIAS" and decision == "BUY":
            confidence += 0.1
        if market_bias == "SHORT_BIAS" and decision == "SELL":
            confidence += 0.1
        if market_bias == "RISK_OFF":
            confidence -= 0.25

        return max(0.0, min(confidence, 0.99))

from quant_ecosystem.intelligence.market.regime_detector import RegimeDetector
from quant_ecosystem.market.market_data_engine import MarketDataEngine


class GlobalIntelligenceEngine:

    def __init__(self):
        self.market_data = MarketDataEngine()
        self.regime_detector = RegimeDetector()

    def analyze(self):
        volatility = self.market_data.get_volatility()
        trend = self.market_data.get_trend()
        regime_advanced = self.regime_detector.detect_advanced(volatility=volatility, trend=trend)
        regime = self.regime_detector.detect(volatility=volatility, trend=trend)
        bias = self._bias_from_regime(regime)

        report = {
            "volatility": round(volatility, 4),
            "trend": trend,
            "regime": regime,
            "regime_advanced": regime_advanced,
            "bias": bias,
        }
        print(f"Global intelligence: {report}")
        return report

    def _bias_from_regime(self, regime):
        if regime == "TREND":
            return "LONG_BIAS"
        if regime == "MEAN_REVERSION":
            return "SHORT_BIAS"
        if regime in {"HIGH_VOLATILITY", "CRISIS"}:
            return "RISK_OFF"
        return "NEUTRAL"

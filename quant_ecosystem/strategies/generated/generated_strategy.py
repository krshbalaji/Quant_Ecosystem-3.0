from quant_ecosystem.strategies.base.base_strategy import BaseStrategy


class GeneratedStrategy(BaseStrategy):

    def __init__(self, strategy_id, feature, threshold):

        self.id = strategy_id
        self.feature = feature
        self.threshold = threshold

    # --------------------------------------------------

    def generate_signal(self, market_data):

        symbol = "NIFTY50"

        value = self._get_feature(symbol, market_data)

        if value is None:
            return None

        if value < self.threshold:
            return {
                "symbol": symbol,
                "side": "BUY",
                "strength": 1.0
            }

        if value > self.threshold + 10:
            return {
                "symbol": symbol,
                "side": "SELL",
                "strength": 1.0
            }

        return None

    # --------------------------------------------------

    def _get_feature(self, symbol, market_data):

        features = market_data.feature_engine

        if self.feature == "rsi":
            return features.get_rsi(symbol)

        if self.feature == "momentum":
            return features.get_momentum(symbol)

        if self.feature == "volatility":
            return features.get_volatility(symbol)

        if self.feature == "atr":
            return features.get_atr(symbol)

        if self.feature == "vwap":
            return features.get_vwap(symbol)

        return None
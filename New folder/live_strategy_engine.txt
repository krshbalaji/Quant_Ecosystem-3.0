import logging

logger = logging.getLogger(__name__)


class LiveStrategyEngine:

    def __init__(self, strategy_registry):

        self.registry = strategy_registry

        try:
            self.strategies = strategy_registry.load()
        except Exception as e:
            logger.warning(f"Strategy load failed: {e}")
            self.strategies = {}

        logger.info(f"LiveStrategyEngine initialized ({len(self.strategies)} strategies)")

    def run(self, market_data):

        signals = []

        for name, strategy in self.strategies.items():

            try:
                signal = strategy(market_data)

                if signal:
                    signals.append(signal)

            except Exception as e:
                logger.warning(f"Strategy {name} error: {e}")

        return signals
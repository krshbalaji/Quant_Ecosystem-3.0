import logging

logger = logging.getLogger(__name__)


class LiveStrategyEngine:

    def __init__(self, strategy_registry=None, selector=None, **kwargs):

        self.registry = strategy_registry
        self.selector = selector

        self.active_strategies = []

        if self.registry:

            try:
                self.active_strategies = self.registry.load()

            except Exception as e:

                logger.warning("Strategy load failed: %s", e)

                self.active_strategies = []

    def get_active_strategies(self):

        return list(self.active_strategies)

    def load_strategies(self):

        try:

            strategies = self.registry.load()

            self.active_strategies = strategies

            logger.info(
                "Loaded %d strategies from registry",
                len(strategies),
            )

        except Exception as e:

            logger.warning("Strategy load failed: %s", e)

            self.active_strategies = []

    def run(self, market_data):

        signals = []

        for strategy in self.active_strategies:

            try:

                signal = strategy(market_data)

                if signal:

                    signals.append(signal)

            except Exception as e:

                logger.warning("Strategy execution error: %s", e)

        return signals
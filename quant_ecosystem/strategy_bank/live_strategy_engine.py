import logging
import time
import uuid

logger = logging.getLogger(__name__)


class LiveStrategyEngine:

    def __init__(self, strategy_registry, execution_authority=None):

        self.registry = strategy_registry
        self.execution_authority = execution_authority

        try:
            self.strategies = strategy_registry.load()
        except Exception as e:
            logger.warning(f"Strategy load failed: {e}")
            self.strategies = {}

        logger.info(f"LiveStrategyEngine initialized ({len(self.strategies)} strategies)")

    def _envelope(self, sid, raw_signal):

        if not isinstance(raw_signal, dict):
            return None

        token = None
        epoch = None

        if self.execution_authority:
            token = self.execution_authority.issue_token(sid)
            epoch = self.execution_authority.get_activation_epoch(sid)

        raw_signal["strategy_id"] = sid
        raw_signal["execution_token"] = token or str(uuid.uuid4())
        raw_signal["activation_epoch"] = epoch or int(time.time())

        return raw_signal

    def run(self, market_data):

        signals = []

        for sid, strategy in self.strategies.items():

            try:
                raw_signal = strategy(market_data)

                if raw_signal:
                    env = self._envelope(sid, raw_signal)
                    if env:
                        signals.append(env)

            except Exception as e:
                logger.warning(f"Strategy {sid} error: {e}")

        return signals
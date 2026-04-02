import logging
import time
import uuid

logger = logging.getLogger(__name__)


class LiveStrategyEngine:

    def __init__(self, strategy_registry, execution_authority=None):

        self.registry = strategy_registry
        self.execution_authority = execution_authority

        logger.info("LiveStrategyEngine initialized (dynamic registry mode)")

    def _get_live_strategies(self):

        try:
            return self.registry.load()
        except Exception as e:
            logger.warning(f"Strategy reload failed: {e}")
            return {}

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
        fallback = self._fallback_signal(market_data)

        strategies = self._get_live_strategies()

        for sid, strategy in strategies.items():

            try:
                raw_signal = strategy(market_data)

                if raw_signal:
                    env = self._envelope(sid, raw_signal)
                    if env:
                        signals.append(env)

            except Exception as e:
                logger.warning(f"Strategy {sid} error: {e}")

        if not signals and fallback:
            signals.append(fallback)

        return signals

    def generate_signal(self, market_data):
        signals = self.run(market_data)
        if not signals:
            return None
        return signals[0]

    def _fallback_signal(self, market_data):
        payload = dict(market_data or {})
        symbols = list(payload.get("symbols", []) or [])
        symbol = str(payload.get("symbol") or (symbols[0] if symbols else "")).strip()
        if not symbol:
            return None

        regime = str(payload.get("regime", "RANGE")).upper()
        price = payload.get("price")
        side = "BUY"
        strategy_id = "fallback_range"
        confidence = 0.2

        if regime in {"TREND", "TRENDING_BULL", "TRENDING_BEAR"}:
            side = "BUY"
            strategy_id = "fallback_trend"
            confidence = 0.3
        elif regime in {"HIGH_VOLATILITY", "VOLATILE", "CRISIS"}:
            side = "SELL"
            strategy_id = "fallback_volatility"
            confidence = 0.25

        signal = {
            "symbol": symbol,
            "side": side,
            "strategy": strategy_id,
            "strategy_id": strategy_id,
            "confidence": confidence,
            "participation": 0.6,
            "price": price,
            "trade_type": "FALLBACK",
            "regime": regime,
        }
        return self._envelope(strategy_id, signal)

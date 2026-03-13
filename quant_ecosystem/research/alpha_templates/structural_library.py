import random


class AlphaStructuralLibrary:

    def __init__(self):

        self.templates = [

            self._breakout_template,
            self._mean_reversion_template,
            self._momentum_template,
            self._volatility_compression_template,
            self._trend_pullback_template,
        ]

    # -------------------------------------------------

    def sample_template(self):

        fn = random.choice(self.templates)

        return fn()

    # -------------------------------------------------

    def _breakout_template(self):

        return {
            "family": "breakout",
            "lookback": random.randint(10, 60),
            "threshold": random.uniform(0.8, 2.5),
            "hold_bars": random.randint(3, 20),
        }

    # -------------------------------------------------

    def _mean_reversion_template(self):

        return {
            "family": "mean_reversion",
            "rsi_period": random.randint(5, 20),
            "entry_level": random.randint(20, 35),
            "exit_level": random.randint(55, 70),
        }

    # -------------------------------------------------

    def _momentum_template(self):

        return {
            "family": "momentum",
            "ema_fast": random.randint(5, 20),
            "ema_slow": random.randint(20, 80),
            "confirm_bars": random.randint(1, 5),
        }

    # -------------------------------------------------

    def _volatility_compression_template(self):

        return {
            "family": "volatility_compression",
            "bb_period": random.randint(10, 30),
            "compression_threshold": random.uniform(0.2, 0.6),
            "expansion_target": random.uniform(1.2, 3.0),
        }

    # -------------------------------------------------

    def _trend_pullback_template(self):

        return {
            "family": "trend_pullback",
            "trend_period": random.randint(30, 120),
            "pullback_depth": random.uniform(0.3, 0.8),
            "reentry_confirm": random.randint(1, 4),
        }
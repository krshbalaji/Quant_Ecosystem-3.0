import numpy as np


class RegimeDetectorEngine:
    """
    Detects market regime using volatility + trend strength.
    """

    def __init__(self):
        self.last_regime = "neutral"

    def detect(self, closes):

        if len(closes) < 120:
            return "neutral"

        arr = np.array(closes)

        returns = np.diff(arr) / arr[:-1]

        vol = np.std(returns) * 100

        trend = (arr[-1] - arr[-60]) / arr[-60] * 100

        if vol > 1.8:
            regime = "volatile"

        elif abs(trend) > 3:
            regime = "trending"

        else:
            regime = "range"

        self.last_regime = regime
        return regime
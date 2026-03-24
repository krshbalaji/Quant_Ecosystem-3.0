class RegimeShiftDetector:

    def __init__(self):
        self.last_regime = {}

    def detect(self, symbol, resolution, regime_memory):

        current = regime_memory.get_current_regime(symbol, resolution)

        key = (symbol, resolution)

        previous = self.last_regime.get(key)

        self.last_regime[key] = current

        if previous is None:
            return False, current

        return previous != current, current
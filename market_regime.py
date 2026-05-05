def detect_regime(volatility, trend):

    if volatility > 0.03:
        return "HIGH_VOL"

    if trend > 0:
        return "TRENDING"

    return "SIDEWAYS"
def strategy(data):
    close = data["close"]
    if len(close) < 30:
        return "HOLD"

    sma_fast = sum(close[-10:]) / 10
    sma_slow = sum(close[-30:]) / 30

    if sma_fast > sma_slow:
        return "BUY"
    if sma_fast < sma_slow:
        return "SELL"
    return "HOLD"

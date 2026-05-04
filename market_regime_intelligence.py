# market_regime_intelligence.py

from market_data_provider import provider

INDEX_SYMBOLS = ["^NSEI", "^NSEBANK"]

def get_market_regime():

    signals = []

    for idx in INDEX_SYMBOLS:
        md = provider.get_data(idx)
        if not md:
            continue

        price = md["price"]
        high = md["high"]
        low = md["low"]

        volatility = abs(high - low) / price

        if volatility > 0.01:
            signals.append("VOLATILE")
        elif price > (high + low) / 2:
            signals.append("BULL")
        else:
            signals.append("BEAR")

    # ---- decide regime ----
    if "VOLATILE" in signals:
        return "VOLATILE"

    if signals.count("BULL") > signals.count("BEAR"):
        return "BULL"

    return "BEAR"
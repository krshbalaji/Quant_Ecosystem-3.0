from ai_memory import get_bias
from ai_memory import record_trade

record_trade("TCS.NS", "SELL", 500)   # positive pnl
record_trade("RELIANCE.NS", "SELL", -300)  # loss

def score_signal(signal, market_data):
    strength = signal.get("strength", 0)
    symbol = signal.get("symbol")

    price = market_data.get("price", 0)
    high = market_data.get("high", price)
    low = market_data.get("low", price)

    volatility = abs(high - low) / price if price else 0.02

    score = 0

    # base strength
    score += strength * 50

    # volatility
    if volatility > 0.05:
        score -= 20
    elif volatility < 0.02:
        score += 10

    # trend boost
    if strength > 1.0:
        score += 20

    # 🔥 AI LEARNING (NEW)
    bias = get_bias(symbol)

    # normalize bias
    if bias > 0:
        score += min(15, bias / 50)
    elif bias < 0:
        score -= min(15, abs(bias) / 50)

    return score
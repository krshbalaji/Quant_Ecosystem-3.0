import yfinance as yf
import pandas as pd
import datetime

from pre_market_predictor import predict_day_type

UNIVERSE = [
    "^NSEBANK",
    "^NSEI",
    "RELIANCE.NS",
    "HDFCBANK.NS",
    "SBIN.NS",
    "TATASTEEL.NS",
    "ADANIENT.NS"
]

# ---------------- SAFE LAST ---------------- #

def last(x):
    if isinstance(x, pd.Series):
        return float(x.iloc[-1])
    if isinstance(x, pd.DataFrame):
        return float(x.values[-1][0])
    return float(x)

# ---------------- MULTI TF BIAS ---------------- #

def mtf_bias(symbol):

    try:
        df15 = yf.download(symbol, period="5d", interval="15m", progress=False)
        df1h = yf.download(symbol, period="10d", interval="60m", progress=False)

        if len(df15) < 50 or len(df1h) < 50:
            return "UNKNOWN"

        ema_fast_15 = last(df15["Close"].ewm(span=20).mean())
        ema_slow_15 = last(df15["Close"].ewm(span=50).mean())

        ema_fast_1h = last(df1h["Close"].ewm(span=20).mean())
        ema_slow_1h = last(df1h["Close"].ewm(span=50).mean())

        if ema_fast_15 > ema_slow_15 and ema_fast_1h > ema_slow_1h:
            return "BULL"

        if ema_fast_15 < ema_slow_15 and ema_fast_1h < ema_slow_1h:
            return "BEAR"

        return "MIXED"

    except:
        return "UNKNOWN"

def select_strategy(regime_type, participation, gap_strength, trend_strength):

    # -------- TREND LOGIC -------- #

    if regime_type == "TREND":

        if gap_strength > 0.004 and participation > 1.5:
            return {
                "trade_type": "FUTURES_BREAKOUT",
                "strategy_file": "strategy_bank/breakout_momentum.py",
                "mode": "AGGRESSIVE"
            }

        elif trend_strength > 0.002:
            return {
                "trade_type": "FUTURES_INTRADAY",
                "strategy_file": "strategy_bank/ema_pullback.py",
                "mode": "NORMAL"
            }

        else:
            return {
                "trade_type": "MOMENTUM_CHASE",
                "strategy_file": "strategy_bank/confidence_momentum.py",
                "mode": "LATE_TREND"
            }

    # -------- RANGE LOGIC -------- #

    elif regime_type == "RANGE":

        if participation > 1.3:
            return {
                "trade_type": "OPTIONS_SCALP",
                "strategy_file": "strategy_bank/orb_scalp.py",
                "mode": "ACTIVE_RANGE"
            }

        else:
            return {
                "trade_type": "MEAN_REVERSION",
                "strategy_file": "strategy_bank/mean_revert.py",
                "mode": "TIGHT_RANGE"
            }

    # -------- DEAD -------- #

    else:
        return {
            "trade_type": "NO_TRADE",
            "strategy_file": None,
            "mode": "STAY_OUT"
        }
# ---------------- REGIME ---------------- #

def regime(df):

    close = df["Close"]

    ema20 = last(close.ewm(span=20).mean())
    ema50 = last(close.ewm(span=50).mean())

    strength = abs(ema20 - ema50) / last(close)

    vol = last(df["Volume"])
    vol_avg = last(df["Volume"].rolling(20).mean())

    participation = vol / vol_avg if vol_avg != 0 else 0

    if strength > 0.003 and participation > 1.2:
        return "TREND"

    if strength < 0.0015:
        return "RANGE"

    return "MIXED"

# ---------------- SCORE ---------------- #

def score(df):

    close = df["Close"]

    ema20 = last(close.ewm(span=20).mean())
    ema50 = last(close.ewm(span=50).mean())

    atr = last((df["High"] - df["Low"]).rolling(14).mean())
    price = last(close)

    if price == 0:
        return 0

    trend_component = abs(ema20 - ema50) / price
    volatility_component = atr / price

    return trend_component * volatility_component * 100

# ---------------- CAPITAL PLAN ---------------- #

def capital_plan(conviction):

    if conviction > 0.005:
        return 100, "FULL"

    if conviction > 0.002:
        return 70, "THREE-FOURTH"

    if conviction > 0.0007:
        return 40, "HALF"

    if conviction > 0.0003:
        return 20, "LIGHT"

    return 0, "NONE"

    

# ---------------- RANK ---------------- #

def rank_market():

    ranking = {}

    for s in UNIVERSE:

        try:
            print("Checking", s)

            df = yf.download(
                s,
                period="5d",
                interval="5m",
                progress=False
            )

            if df is None or len(df) < 60:
                continue

            ranking[s] = score(df)

        except:
            pass

    if not ranking:
        return None, None

    leader = max(ranking, key=ranking.get)

    return leader, ranking

# ---------------- COMMANDER ---------------- #

def commander():

    print("\n===== INSTITUTIONAL DEPLOYMENT COMMANDER V6 =====\n")

    # -------- STEP 1: RANK MARKET -------- #

    leader, ranking = rank_market()

    if leader is None:
        print("❌ No Data")
        return

    print("\n🔥 Leader:", leader)

    # -------- STEP 2: FETCH DATA -------- #

    df = yf.download(leader, period="5d", interval="5m", progress=False)

    if df is None or len(df) < 60:
        print("❌ Leader data insufficient")
        return

    # -------- STEP 3: CORE METRICS -------- #

    reg = regime(df)
    bias = mtf_bias(leader)
    conviction = ranking[leader]

    price = last(df["Close"])
    
    # -------- STEP 4: ROTATION METRICS -------- #

    prev_close = float(df["Close"].iloc[-2])
    open_price = float(df["Open"].iloc[-1])

    gap_strength = abs(open_price - prev_close) / prev_close

    trend_strength = abs(
        float(df["Close"].ewm(span=20).mean().iloc[-1]) -
        float(df["Close"].ewm(span=50).mean().iloc[-1])
    ) / float(df["Close"].iloc[-1])

    vol_now = float(df["Volume"].iloc[-1])
    vol_avg = float(df["Volume"].rolling(20).mean().iloc[-1])

    participation = vol_now / vol_avg if vol_avg != 0 else 0

    # -------- STEP 5: STRATEGY ROTATION -------- #

    decision = select_strategy(reg, participation, gap_strength, trend_strength)

    # -------- STEP 6: CAPITAL -------- #

    capital_pct, lot_mode = capital_plan(conviction)

    # 🔧 GAP ADJUSTMENT (place here ONLY)

    if gap_strength < 0.001 and reg == "TREND":
        capital_pct = int(capital_pct * 0.6)
    
    # 🔥 Participation override

    if participation > 1.4 and capital_pct == 0:
        capital_pct = 20
        lot_mode = "LIGHT"
    
    def load_strategy_code(path):

        try:
            with open(path, "r") as f:
                return f.read()
        except:
            return None

    # -------- OUTPUT -------- #

    prediction = predict_day_type()

    final_strategy, final_capital, note = fuse_decision(
        prediction,
        reg,
        capital_pct,
        decision["strategy_file"]
    )

    print("\n🔮 PRE-MARKET BIAS:", prediction)

    print("\n🧠 FINAL FUSED DECISION")
    print("Final Strategy →", final_strategy)
    print("Final Capital →", final_capital, "%")
    print("Note →", note)

    # -------- FINAL FILTER -------- #

    trade_type = decision["trade_type"]

    if capital_pct == 0 or trade_type == "NO_TRADE":
        print("\n❌ NO TRADE TODAY")
        return

    print("\n✅ ACTION:")
    print("Deploy strategy in Bulls AI before 9:25 AM")

    # -------- BULLS AI READY OUTPUT -------- #

    if final_strategy and final_strategy != "NO_TRADE":

        code = load_strategy_code(final_strategy)

    print("\n==============================")
    print("📦 BULLS AI READY DEPLOYMENT")
    print("==============================\n")

    print(f"Instrument → {leader}")
    print(f"Trade Type → {decision['trade_type']}")
    print(f"Capital → {final_capital} %\n")

    if code:
        print("------ COPY BELOW ------\n")
        print(code)
        print("\n------ END COPY ------")
    else:
        print("❌ Strategy file not found")

def fuse_decision(prediction, reg, capital_pct, strategy):

    final_strategy = strategy
    final_capital = capital_pct
    note = ""

    # -------- RANGE DOMINANT -------- #
    if prediction == "RANGE":

        if reg == "TREND":
            final_capital = int(capital_pct * 0.6)
            final_strategy = "strategy_bank/orb_scalp.py"
            note = "Range Expected → Reduce size + scalp"

        elif reg == "RANGE":
            final_strategy = "strategy_bank/orb_scalp.py"
            note = "Range Confirmed → Options Scalp"

    # -------- TREND DOMINANT -------- #
    elif prediction == "TREND":

        if reg == "TREND":
            final_capital = int(capital_pct * 1.2)
            note = "Trend Alignment → Aggressive Allowed"

        elif reg == "RANGE":
            final_capital = int(capital_pct * 0.5)
            note = "Mismatch → Wait / Small size"

    # -------- TRAP -------- #
    elif prediction == "TRAP":

        final_capital = int(capital_pct * 0.3)
        final_strategy = "NO_TRADE"
        note = "Trap Risk → Avoid"

    return final_strategy, final_capital, note

    # -------- GET PREDICTION -------- #

    prediction = predict_day_type()   # return "TREND" / "RANGE" / "TRAP"

    # -------- FUSION -------- #

    final_strategy, final_capital, note = fuse_decision(
        prediction,
        reg,
        capital_pct,
        decision["strategy_file"]
    )    
if __name__ == "__main__":
    commander()
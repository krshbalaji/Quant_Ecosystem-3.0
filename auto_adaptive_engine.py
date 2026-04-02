import time
import yfinance as yf
import datetime

SYMBOL = "^NSEBANK"

# -------- SAFE -------- #

def safe(x):
    try:
        return float(x.iloc[-1])
    except:
        return 0.0

# -------- REGIME -------- #

def regime(df):

    close = df["Close"]

    ema20 = safe(close.ewm(span=20).mean())
    ema50 = safe(close.ewm(span=50).mean())

    strength = abs(ema20 - ema50) / safe(close)

    if strength > 0.003:
        return "TREND"
    elif strength < 0.0015:
        return "RANGE"
    else:
        return "MIXED"

# -------- PARTICIPATION -------- #

def participation(df):

    try:
        vol = float(df["Volume"].iloc[-1])
        vol_avg = float(df["Volume"].rolling(20).mean().iloc[-1])

        if vol_avg == 0 or vol_avg != vol_avg:
            return 1.0

        return vol / vol_avg

    except:
        return 1.0

# -------- TIME PHASE -------- #

def time_phase():

    now = datetime.datetime.now().time()

    if now < datetime.time(9,30):
        return "PREMARKET"

    elif now < datetime.time(11,30):
        return "OPEN"

    elif now < datetime.time(14,30):
        return "MID"

    else:
        return "CLOSE"

# -------- DECISION ENGINE -------- #

def decision_engine(reg, part, phase):

    strategy = "NO_TRADE"
    capital = 0
    note = ""

    # OPEN SESSION
    if phase == "OPEN":

        if reg == "TREND" and part > 1.2:
            strategy = "EMA_PULLBACK"
            capital = 50
            note = "Strong trend"

        elif reg == "RANGE":
            strategy = "ORB_SCALP"
            capital = 30
            note = "Opening range"

    # MID SESSION
    elif phase == "MID":

        if part < 0.8:
            strategy = "NO_TRADE"
            capital = 0
            note = "Participation drop"

        elif reg == "TREND":
            strategy = "EMA_PULLBACK"
            capital = 30
            note = "Trend continuation"

        elif reg == "MIXED":
            strategy = "SCALP"
            capital = 20
            note = "Volatile mixed"

    # CLOSING
    elif phase == "CLOSE":

        strategy = "NO_TRADE"
        capital = 0
        note = "End of session"

    return strategy, capital, note

# -------- LOOP -------- #

def run_engine():

    print("\n===== AUTO ADAPTIVE ENGINE V12 =====\n")

    while True:

        df = yf.download(SYMBOL, period="1d", interval="5m", progress=False)

        if df is None or len(df) < 50:
            print("❌ No data")
            time.sleep(300)
            continue

        reg = regime(df)
        part = participation(df)
        phase = time_phase()

        strategy, capital, note = decision_engine(reg, part, phase)

        print("\n🧠 LIVE DECISION")
        print("Regime:", reg)
        print("Participation:", round(part,2))
        print("Phase:", phase)

        print("\n🎯 Action:")
        print("Strategy:", strategy)
        print("Capital:", capital, "%")
        print("Note:", note)

        # refresh every 5 min
        time.sleep(300)

# -------- RUN -------- #

if __name__ == "__main__":
    run_engine()
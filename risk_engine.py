import math

# -------- CONFIG -------- #

TOTAL_CAPITAL = 100000   # change as per your account
RISK_PER_TRADE = 0.01    # 1% risk
MAX_DAILY_LOSS = 0.03    # 3% stop for the day

# -------- POSITION SIZING -------- #

def position_size(entry, stop_loss):

    risk_amount = TOTAL_CAPITAL * RISK_PER_TRADE

    risk_per_share = abs(entry - stop_loss)

    if risk_per_share == 0:
        return 0

    qty = risk_amount / risk_per_share

    return math.floor(qty)

# -------- STOP LOSS LOGIC -------- #

def calculate_sl(df):

    # simple ATR based SL
    atr = (df["High"] - df["Low"]).rolling(14).mean().iloc[-1]

    price = df["Close"].iloc[-1]

    sl = price - atr  # for long

    return float(sl)

# -------- DAILY LOSS CONTROL -------- #

def allowed_to_trade(current_loss):

    max_loss = TOTAL_CAPITAL * MAX_DAILY_LOSS

    if current_loss >= max_loss:
        return False

    return True
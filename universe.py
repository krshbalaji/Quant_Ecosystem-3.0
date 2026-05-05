# universe.py
# --- Compatibility for portfolio intelligence ---
SYMBOL_UNIVERSE = {
    "IT": ["TCS.NS", "INFY.NS"],
    "BANK": ["HDFCBANK.NS", "ICICIBANK.NS"],
    "ENERGY": ["RELIANCE.NS"],
    "AUTO": ["MARUTI.NS"],
    "METAL": ["TATASTEEL.NS"]
}

LARGE_CAP = [
    "TCS.NS", "INFY.NS", "RELIANCE.NS",
    "HDFCBANK.NS", "ICICIBANK.NS"
]

MID_CAP = [
    "DIXON.NS", "ASTRAL.NS", "POLYCAB.NS"
]

SMALL_CAP = [
    "KPITTECH.NS", "COFORGE.NS"
]


def get_dynamic_universe(volatility_mode=False):

    if volatility_mode:
        return LARGE_CAP + MID_CAP + SMALL_CAP

    return LARGE_CAP
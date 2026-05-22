# config.py
import os
from dotenv import load_dotenv
load_dotenv()

def load_api_key():
    # 1. ENV (fastest, primary)
    key = os.getenv("API_KEY")
    if key:
        return key

    # 2. Secret Manager (cloud)
    try:
        from config.secret_loader import get_secret
        return get_secret("QE_API_KEY")
    except:
        pass

    # 3. Local fallback (.env or hard fallback)
    return "LOCAL_DEV_KEY"


class Config:
    CLOUD_BASE_URL = os.getenv(
        "CLOUD_BASE_URL",
        "https://quant-ecosystem-shadow-16683273546.asia-south1.run.app"
    )

    # 🔥 Compatibility aliases (fix all current & future mismatches)
    API_BASE_URL = CLOUD_BASE_URL

    API_KEY = load_api_key()

    MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))
    BACKOFF_FACTOR = float(os.getenv("BACKOFF_FACTOR", 0.3))
    TIMEOUT = int(os.getenv("TIMEOUT", 5))

    MODE = os.getenv("MODE", "PAPER")
       
    # 🔥 Alias for http_client expectation
    REQUEST_TIMEOUT = TIMEOUT

    # ===== CAPITAL =====
    ACCOUNT_CAPITAL = 100000   # default (you can change anytime)

    # ===== RISK =====
    RISK_PER_TRADE_PCT = 0.01   # 1%
    MAX_DAILY_RISK_PCT = 0.03   # 3%

    # ===== TRADE CONTROL =====
    MAX_TRADES_PER_DAY = 5
    MAX_CONCURRENT = 1
    
    TRADE_SYMBOLS = ["TCS.NS", "RELIANCE.NS"]
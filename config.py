from dotenv import load_dotenv
import os

load_dotenv()

TRADE_SYMBOLS = os.getenv("TRADE_SYMBOLS", "").split(",")
TRADE_SYMBOLS = [s.strip() for s in os.getenv("TRADE_SYMBOLS", "").split(",") if s.strip()]
def _int_env(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)).strip())
    except (ValueError, TypeError):
        return default


class Config:
    API_BASE_URL = os.getenv("API_BASE_URL", "")
    API_KEY = os.getenv("API_KEY", "")
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 10))
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))
    LOCAL_FALLBACK_ENABLED = os.getenv("LOCAL_FALLBACK_ENABLED", "true").lower() == "true"
    EXECUTION_MODE = os.getenv("EXECUTION_MODE", "auto")

    TRADE_SYMBOLS = [s.strip() for s in os.getenv("TRADE_SYMBOLS", "").split(",") if s.strip()]

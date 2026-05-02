from dotenv import load_dotenv
import os

load_dotenv()


def _int_env(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)).strip())
    except (ValueError, TypeError):
        return default


class Config:
    API_BASE_URL = os.getenv("API_BASE_URL", "").rstrip("/")
    API_KEY = os.getenv("API_KEY", os.getenv("CLOUD_API_KEY", ""))
    REQUEST_TIMEOUT = _int_env("REQUEST_TIMEOUT", 10)
    MAX_RETRIES = _int_env("MAX_RETRIES", 3)
    LOCAL_FALLBACK_ENABLED = str(os.getenv("LOCAL_FALLBACK_ENABLED", "true")).strip().lower() in (
        "1",
        "true",
        "yes",
        "y",
    )
    EXECUTION_MODE = os.getenv("EXECUTION_MODE", "auto").strip().lower()

    if EXECUTION_MODE not in {"auto", "cloud", "local"}:
        EXECUTION_MODE = "auto"

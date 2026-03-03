import os
from dotenv import load_dotenv

load_dotenv()

class Env:

    FYERS_CLIENT_ID = os.getenv("FYERS_CLIENT_ID") or os.getenv("FYERS_APP_ID")
    FYERS_SECRET_KEY = os.getenv("FYERS_SECRET_KEY")
    FYERS_REDIRECT_URI = os.getenv("FYERS_REDIRECT_URI")
    COINSWITCH_API_KEY = os.getenv("COINSWITCH_API_KEY")
    COINSWITCH_API_SECRET = os.getenv("COINSWITCH_API_SECRET")
    COINSWITCH_BASE_URL = os.getenv("COINSWITCH_BASE_URL")

    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

    LIVE_TRADING = os.getenv("LIVE_TRADING","false").lower() == "true"

    CAPITAL = float(os.getenv("CAPITAL",100000))

    MODE = os.getenv("MODE","paper")

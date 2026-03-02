import os
from dotenv import load_dotenv

load_dotenv()

class Env:

    FYERS_CLIENT_ID = os.getenv("FYERS_CLIENT_ID")
    FYERS_SECRET_KEY = os.getenv("FYERS_SECRET_KEY")
    FYERS_REDIRECT_URI = os.getenv("FYERS_REDIRECT_URI")

    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

    LIVE_TRADING = os.getenv("LIVE_TRADING","false").lower() == "true"

    CAPITAL = float(os.getenv("CAPITAL",100000))

    MODE = os.getenv("MODE","paper")
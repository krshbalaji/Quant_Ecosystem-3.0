import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")

last_update_id = None

def get_command():

    global last_update_id

    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
        res = requests.get(url, timeout=5).json()

        for update in res.get("result", []):
            uid = update["update_id"]

            if last_update_id and uid <= last_update_id:
                continue

            last_update_id = uid

            msg = update.get("message", {}).get("text", "").lower()
            return msg

    except Exception:
        return None

    return None
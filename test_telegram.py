import os
import requests
from dotenv import load_dotenv

# load .env
load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

print("TOKEN:", TOKEN)
print("CHAT:", CHAT_ID)

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

print("Telegram URL:", url)

r = requests.post(
    url,
    json={
        "chat_id": CHAT_ID,
        "text": "🚀 Quant Ecosystem Telegram test successful"
    }
)

print(r.text)
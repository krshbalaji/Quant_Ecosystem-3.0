# telegram_control.py

import requests
import time
import os
from dotenv import load_dotenv
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text
    }

    try:
        res = requests.post(url, json=payload, timeout=5)
        print(f"[TELEGRAM STATUS] {res.status_code}")
    except Exception as e:
        print(f"[TELEGRAM ERROR] {e}")


def ask_user(symbol, side, price, timeout=20):
    """
    Sends signal to Telegram and waits for YES/NO response.
    If no response → auto skip (safe mode).
    """

    message = f"""
📊 TRADE SIGNAL

Symbol: {symbol}
Side: {side}
Price: {price}

Reply:
YES → Take trade
NO → Skip
    """

    send_message(message)

    print("[WAITING USER INPUT - TELEGRAM]")

    start_time = time.time()

    last_update_id = None

    while time.time() - start_time < timeout:

        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
            response = requests.get(url, timeout=5).json()

            if "result" not in response:
                continue

            for update in response["result"]:

                update_id = update["update_id"]

                if last_update_id is not None and update_id <= last_update_id:
                    continue

                last_update_id = update_id

                if "message" not in update:
                    continue

                text = update["message"].get("text", "").strip().lower()

                if text == "yes":
                    send_message("✅ Trade Confirmed")
                    return True

                if text == "no":
                    send_message("❌ Trade Skipped")
                    return False

        except Exception as e:
            print(f"[TELEGRAM POLL ERROR] {e}")

        time.sleep(2)

    send_message("⌛ No response → Trade skipped")
    return False

def get_command(timeout=20):
    """
    Lightweight command listener (used by precision_executor).
    Returns: 'yes', 'no', or None
    """

    start_time = time.time()
    last_update_id = None

    while time.time() - start_time < timeout:

        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
            response = requests.get(url, timeout=5).json()

            if "result" not in response:
                continue

            for update in response["result"]:

                update_id = update["update_id"]

                if last_update_id is not None and update_id <= last_update_id:
                    continue

                last_update_id = update_id

                if "message" not in update:
                    continue

                text = update["message"].get("text", "").strip().lower()

                if text.startswith("y"):
                    return True

                if text.startswith("n"):
                    return False

                if text in ["yes", "no"]:
                    return text

        except Exception as e:
            print(f"[TELEGRAM COMMAND ERROR] {e}")

        time.sleep(2)

    return None

def ask_trade_details(symbol, side, price):
    send_message(f"""
📊 TRADE SIGNAL

Symbol: {symbol}
Side: {side}
Price: {price}

Reply:
YES → proceed
NO → skip
""")

    cmd = get_command(timeout=20)

    if not cmd or str(cmd).lower().startswith("n"):
        send_message("❌ Trade Skipped")
        return None

    # Step 2 → ask qty
    send_message("Enter Qty (default 1):")
    qty_input = get_command(timeout=20)

    try:
        qty = int(qty_input)
    except:
        qty = 1

    # Step 3 → ask price override
    send_message("Enter Price or type MARKET:")
    price_input = get_command(timeout=20)

    if price_input and str(price_input).lower() != "market":
        try:
            if user_input.upper() == "MARKET":
                price = None
            else:
                try:
                    price = float(user_input)
                except:
                    price = entry_price  # fallback to real price, NOT 1.0
                    
        except:
            pass

    # Step 4 → final confirmation
    send_message(f"""
Confirm Trade?

{symbol} {side}
Qty: {qty}
Price: {price}

YES → Confirm
NO → Cancel
""")

    decision = ask_trade_details(symbol, side, entry)

    if decision is None:
        send_message("❌ Trade Skipped")
        return None

    final = get_command(timeout=20)

    if not final or str(final).lower().startswith("n"):
        send_message("❌ Trade Cancelled")
        return None

    return qty, price 

    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "✅ Confirm", "callback_data": "YES"},
                {"text": "❌ Skip", "callback_data": "NO"}
            ]
        ]
    }   
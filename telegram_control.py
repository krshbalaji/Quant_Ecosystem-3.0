import requests
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

BASE = f"https://api.telegram.org/bot{TOKEN}"

# ---- GLOBAL STATE ----
trade_state = {}
last_update_id = None
panel_message_id = None


# ---------------- SEND / UPDATE PANEL ----------------
def render_panel():

    text = f"""
📊 *TRADE PANEL*

{trade_state['symbol']} | {trade_state['side']}
Entry: {trade_state['entry']}

Qty: {trade_state['qty']}
Price: {trade_state['price']}
"""

    buttons = {
        "inline_keyboard": [
            [
                {"text": "➖ Qty", "callback_data": "qty_dec"},
                {"text": "➕ Qty", "callback_data": "qty_inc"}
            ],
            [
                {"text": "💰 -", "callback_data": "price_dec"},
                {"text": "💰 +", "callback_data": "price_inc"}
            ],
            [
                {"text": "⚡ MARKET", "callback_data": "market"}
            ],
            [
                {"text": "✅ EXECUTE", "callback_data": "execute"},
                {"text": "❌ CANCEL", "callback_data": "cancel"}
            ]
        ]
    }

    return text, buttons


def send_or_update_panel():

    global panel_message_id

    text, buttons = render_panel()

    if panel_message_id is None:
        res = requests.post(f"{BASE}/sendMessage", json={
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": buttons
        }).json()

        panel_message_id = res["result"]["message_id"]

    else:
        requests.post(f"{BASE}/editMessageText", json={
            "chat_id": CHAT_ID,
            "message_id": panel_message_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": buttons
        })


# ---------------- INIT PANEL ----------------
def start_trade_panel(symbol, side, entry):

    global trade_state

    trade_state = {
        "symbol": symbol,
        "side": side,
        "entry": entry,
        "qty": 1,
        "price": entry
    }

    send_or_update_panel()

# -------- BACKWARD COMPATIBILITY --------

def send_message(text):
    import requests

    requests.post(f"{BASE}/sendMessage", json={
        "chat_id": CHAT_ID,
        "text": text
    })


def ask_trade_details(*args, **kwargs):
    # redirect to new system
    return None

# ---------------- HANDLE BUTTONS ----------------
def process_callbacks():

    global last_update_id

    res = requests.get(f"{BASE}/getUpdates").json()

    for upd in res.get("result", []):

        uid = upd["update_id"]

        trade_state = {
            "mode": "IDLE",   # IDLE / PANEL / EXECUTING
            "data": None
        }

        if last_update_id and uid <= last_update_id:
            continue

        last_update_id = uid

        if "callback_query" not in upd:
            continue

        data = upd["callback_query"]["data"]

        # ---- MODIFY STATE ----
        if data == "qty_inc":
            trade_state["qty"] += 1

        elif data == "qty_dec":
            trade_state["qty"] = max(1, trade_state["qty"] - 1)

        elif data == "price_inc":
            trade_state["price"] += 1

        elif data == "price_dec":
            trade_state["price"] -= 1

        elif data == "market":
            trade_state["price"] = "MARKET"

        elif data == "execute":
            trade_state["mode"] = "EXECUTE"
            return "EXECUTE", trade_state

        elif data == "cancel":
            trade_state["mode"] = "CANCEL"
            return "CANCEL", None

        if price == "MARKET":
            order_type = "MARKET"
        else:
            order_type = "LIMIT"
            
        if data == "trade":
            start_trade_panel("HDFCBANK.NS", "SELL", 773.6)

        elif data == "strike":
            send_message("⚡ Strike Mode Activated")

        elif data == "ai":
            send_message("🧠 AI Mode Running")

        elif data == "settings":
            send_message("⚙️ Settings Panel")    

        # update UI after every click
        send_or_update_panel()

    return None, None
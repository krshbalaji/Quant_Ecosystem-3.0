import requests
import os
import time

from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

BASE = f"https://api.telegram.org/bot{TOKEN}"

# =========================================================
# GLOBAL STATE
# =========================================================

BROKERS = [
    "PAPER",
    "FYERS",
    "ZERODHA"
]

STRATEGIES = [
    "SCALP",
    "INTRADAY",
    "SWING",
    "BREAKOUT"
]

trade_state = {
    "active": False,
    "symbol": None,
    "side": None,
    "entry": None,
    "qty": 1,
    "price": "MARKET",
    "status": "IDLE",
    "broker": "PAPER",
    "strategy": "SCALP",
    "regime": "UNKNOWN"
}

last_update_id = None
panel_message_id = None


# =========================================================
# SIMPLE MESSAGE
# =========================================================

def send_message(text):

    try:

        r = requests.post(
            f"{BASE}/sendMessage",
            json={
                "chat_id": CHAT_ID,
                "text": text,
                "parse_mode": "Markdown"
            },
            timeout=10
        )

        print("[TELEGRAM STATUS]", r.status_code)

    except Exception as e:
        print("[TELEGRAM ERROR]", e)


# =========================================================
# CALLBACK ACK
# =========================================================

def answer_callback(callback_id, text="Updated"):

    try:

        requests.post(
            f"{BASE}/answerCallbackQuery",
            json={
                "callback_query_id": callback_id,
                "text": text,
                "show_alert": False
            },
            timeout=10
        )

    except Exception as e:
        print("[CALLBACK ACK ERROR]", e)


# =========================================================
# PANEL UI
# =========================================================

def render_panel():

    symbol = trade_state.get("symbol", "N/A")
    side = trade_state.get("side", "N/A")
    entry = trade_state.get("entry", "N/A")
    qty = trade_state.get("qty", 1)
    price = trade_state.get("price", "MARKET")
    status = trade_state.get("status", "WAITING")
    broker = trade_state.get("broker", "PAPER")
    strategy = trade_state.get("strategy", "SCALP")
    regime = trade_state.get("regime", "UNKNOWN")

    text = f"""
🧠 *PRECISION EXECUTION TERMINAL*

━━━━━━━━━━━━━━━

📈 *Instrument:* `{symbol}`
📊 *Regime:* `{regime}`
⚡ *Strategy:* `{strategy}`
🧭 *Side:* `{side}`

━━━━━━━━━━━━━━━

🎯 *Entry:* `{entry}`

📦 *Qty:* `{qty}`
💰 *Price:* `{price}`

🏦 *Broker:* `{broker}`

━━━━━━━━━━━━━━━

🟡 *Status:* `{status}`
"""

    buttons = {
        "inline_keyboard": [

            [
                {
                    "text": "➖ Qty",
                    "callback_data": "qty_dec"
                },
                {
                    "text": "➕ Qty",
                    "callback_data": "qty_inc"
                }
            ],

            [
                {
                    "text": "💰 Price -",
                    "callback_data": "price_dec"
                },
                {
                    "text": "💰 Price +",
                    "callback_data": "price_inc"
                }
            ],

            [
                {
                    "text": "⚡ MARKET",
                    "callback_data": "market"
                }
            ],

            [
                {
                    "text": f"🏦 {broker}",
                    "callback_data": "broker_next"
                },
                {
                    "text": f"⚡ {strategy}",
                    "callback_data": "strategy_next"
                }
            ],

            [
                {
                    "text": "✅ EXECUTE",
                    "callback_data": "execute"
                },
                {
                    "text": "❌ CANCEL",
                    "callback_data": "cancel"
                }
            ]
        ]
    }

    return text, buttons


# =========================================================
# SEND / UPDATE PANEL
# =========================================================

def send_or_update_panel():

    global panel_message_id

    text, buttons = render_panel()

    try:

        # FIRST SEND
        if panel_message_id is None:

            r = requests.post(
                f"{BASE}/sendMessage",
                json={
                    "chat_id": CHAT_ID,
                    "text": text,
                    "parse_mode": "Markdown",
                    "reply_markup": buttons
                },
                timeout=10
            ).json()

            if r.get("ok"):
                panel_message_id = r["result"]["message_id"]

        # LIVE UPDATE
        else:

            requests.post(
                f"{BASE}/editMessageText",
                json={
                    "chat_id": CHAT_ID,
                    "message_id": panel_message_id,
                    "text": text,
                    "parse_mode": "Markdown",
                    "reply_markup": buttons
                },
                timeout=10
            )

    except Exception as e:
        print("[PANEL ERROR]", e)


# =========================================================
# START PANEL
# =========================================================

def start_trade_panel(symbol, side, entry, regime="UNKNOWN"):

    global trade_state

    trade_state = {
        "active": True,
        "symbol": symbol,
        "side": side,
        "entry": entry,
        "qty": 1,
        "price": entry,
        "status": "WAITING INPUT",
        "broker": "PAPER",
        "strategy": "SCALP",
        "regime": regime
    }

    print("[START PANEL]", trade_state)

    send_or_update_panel()


# =========================================================
# CALLBACK ENGINE
# =========================================================

def process_callbacks():

    global last_update_id
    global trade_state

    try:

        r = requests.get(
            f"{BASE}/getUpdates",
            timeout=10
        ).json()

    except Exception as e:
        print("[CALLBACK ERROR]", e)
        return None, None

    for upd in r.get("result", []):

        uid = upd["update_id"]

        if last_update_id is not None and uid <= last_update_id:
            continue

        last_update_id = uid

        if "callback_query" not in upd:
            continue

        callback = upd["callback_query"]

        callback_id = callback["id"]

        data = callback["data"]

        print("[CALLBACK]", data)

        # =====================================================
        # QTY
        # =====================================================

        if data == "qty_inc":

            trade_state["qty"] += 1

            answer_callback(callback_id, "Qty Increased")

        elif data == "qty_dec":

            trade_state["qty"] = max(
                1,
                trade_state["qty"] - 1
            )

            answer_callback(callback_id, "Qty Reduced")

        # =====================================================
        # PRICE
        # =====================================================

        elif data == "price_inc":

            if trade_state["price"] == "MARKET":
                trade_state["price"] = trade_state["entry"]

            trade_state["price"] += 1

            answer_callback(callback_id, "Price Increased")

        elif data == "price_dec":

            if trade_state["price"] == "MARKET":
                trade_state["price"] = trade_state["entry"]

            trade_state["price"] -= 1

            answer_callback(callback_id, "Price Reduced")

        # =====================================================
        # MARKET
        # =====================================================

        elif data == "market":

            trade_state["price"] = "MARKET"

            answer_callback(callback_id, "Market Order Enabled")

        # =====================================================
        # BROKER SWITCH
        # =====================================================

        elif data == "broker_next":

            current = trade_state["broker"]

            idx = BROKERS.index(current)

            idx = (idx + 1) % len(BROKERS)

            trade_state["broker"] = BROKERS[idx]

            answer_callback(
                callback_id,
                f"Broker → {BROKERS[idx]}"
            )

        # =====================================================
        # STRATEGY SWITCH
        # =====================================================

        elif data == "strategy_next":

            current = trade_state["strategy"]

            idx = STRATEGIES.index(current)

            idx = (idx + 1) % len(STRATEGIES)

            trade_state["strategy"] = STRATEGIES[idx]

            answer_callback(
                callback_id,
                f"Strategy → {STRATEGIES[idx]}"
            )

        # =====================================================
        # EXECUTE
        # =====================================================

        elif data == "execute":

            trade_state["status"] = "EXECUTING"

            send_or_update_panel()

            answer_callback(callback_id, "Executing Trade")

            return "EXECUTE", trade_state

        # =====================================================
        # CANCEL
        # =====================================================

        elif data == "cancel":

            trade_state["status"] = "CANCELLED"

            send_or_update_panel()

            answer_callback(callback_id, "Trade Cancelled")

            return "CANCEL", trade_state

        # =====================================================
        # LIVE PANEL UPDATE
        # =====================================================

        send_or_update_panel()

    return None, None
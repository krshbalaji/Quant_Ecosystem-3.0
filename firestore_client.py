from google.cloud import firestore
from datetime import datetime

db = firestore.Client()
COLLECTION = "portfolio"


def get_positions():
    try:
        docs = db.collection("portfolio").stream()

        positions = {}

        for doc in docs:
            positions[doc.id] = doc.to_dict()

        return positions

    except Exception as e:
        print("[DB ERROR]", e)
        return {}   # 🔥 NEVER return None


def update_position(symbol, side, qty, price=None):
    db.collection("portfolio").document(symbol).set({
        "side": side,
        "qty": qty,
        "entry_price": price,   # ✅ REQUIRED
        "timestamp": datetime.utcnow().isoformat()
    })

   
def close_position(symbol):
    db.collection(COLLECTION).document(symbol).delete()


def log_trade(symbol, side, qty, entry_price, exit_price, pnl):
    db.collection("trade_history").add({
        "symbol": symbol,
        "side": side,
        "qty": qty,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "pnl": pnl,
        "timestamp": datetime.utcnow().isoformat()
    })


def get_trade_history():
    docs = db.collection("trade_history").stream()
    return [doc.to_dict() for doc in docs]


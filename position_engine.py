import json
import os

POS_FILE = "positions.json"


def load_positions():
    if not os.path.exists(POS_FILE):
        return {}

    try:
        return json.load(open(POS_FILE))
    except:
        return {}


def save_positions(data):
    json.dump(data, open(POS_FILE, "w"), indent=2)


def add_position(order):
    positions = load_positions()

    positions[order["symbol"]] = {
        "qty": order["qty"],
        "entry_price": order["price"],
        "stop_loss": order["stop_loss"],
        "take_profit": order["take_profit"]
    }

    save_positions(positions)


def remove_position(symbol):
    positions = load_positions()

    if symbol in positions:
        del positions[symbol]

    save_positions(positions)


def get_positions():
    return load_positions()
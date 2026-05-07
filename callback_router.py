from trade_state import ACTIVE_TRADES
from dashboard import update_dashboard
from precision_executor import execute_signal

def handle_callback(action, trade_id):

    trade = ACTIVE_TRADES.get(trade_id)

    if not trade:
        return

    if action == "QTY_UP":
        trade["qty"] += 1

    elif action == "QTY_DOWN":
        trade["qty"] = max(1, trade["qty"] - 1)

    elif action == "PRICE_MARKET":
        trade["price"] = "MARKET"

    elif action == "EXECUTE":

        execute_signal(
            trade["symbol"],
            trade["side"],
            trade["qty"],
            trade["price"]
        )

        trade["status"] = "EXECUTED"

    elif action == "CANCEL":
        trade["status"] = "CANCELLED"

    update_dashboard(trade_id)
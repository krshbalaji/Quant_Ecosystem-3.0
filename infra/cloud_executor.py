from broker_adapter import BrokerAdapter

broker = BrokerAdapter(mode="paper")


def execute_cloud_trade(data):
    try:
        # ✅ extract correctly
        symbol = data.get("symbol")
        side = data.get("side")
        qty = data.get("qty")

        # --- validation
        if not symbol or not side or not qty:
            return {"success": False, "error": "invalid payload"}

        # --- execute via broker
        broker.place_order(symbol, side, qty)

        return {"success": True}

    except Exception as e:
        return {"success": False, "error": str(e)}
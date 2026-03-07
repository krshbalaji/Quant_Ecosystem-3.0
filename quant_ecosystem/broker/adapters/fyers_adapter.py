class FyersAdapter:

    def __init__(self, app_id, access_token, **kwargs):
        self.app_id = app_id
        self.access_token = access_token
        self.client = None

    def login(self):
        try:
            from fyers_apiv3 import fyersModel
        except Exception as exc:
            raise RuntimeError("fyers-apiv3 package not installed") from exc

        token = f"{self.app_id}:{self.access_token}" if self.app_id else self.access_token
        self.client = fyersModel.FyersModel(client_id=self.app_id, token=token, log_path="")
        return True

    def place_order(self, symbol, side, qty, order_type=2, product_type="INTRADAY"):
        self._ensure_client()
        api_side = 1 if str(side).upper() == "BUY" else -1
        payload = {
            "symbol": symbol,
            "qty": int(qty),
            "type": int(order_type),  # 1=limit,2=market
            "side": api_side,
            "productType": product_type,
            "validity": "DAY",
            "offlineOrder": False,
            "disclosedQty": 0,
            "stopPrice": 0,
            "limitPrice": 0,
            "takeProfit": 0,
            "stopLoss": 0,
        }
        return self.client.place_order(payload)

    def get_positions(self):
        self._ensure_client()
        return self.client.positions()

    def get_orderbook(self):
        self._ensure_client()
        return self.client.orderbook()

    def get_tradebook(self):
        self._ensure_client()
        return self.client.tradebook()

    def get_funds(self):
        self._ensure_client()
        return self.client.funds()

    def _ensure_client(self):
        if not self.client:
            raise RuntimeError("FYERS client not initialized. Call login() first.")

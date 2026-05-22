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

        token = self.access_token
        self.client = fyersModel.FyersModel(client_id=self.app_id, token=token, log_path="")
        return True

    def place_order(
        self,
        symbol,
        side,
        qty,
        price=None,
        fee=0.0,
        meta=None,
        order_type=2,
        product_type="INTRADAY"
    ):
        self._ensure_client()

        payload = {
            "symbol": symbol,
            "qty": qty,
            "type": order_type,
            "side": 1 if str(side).upper() == "BUY" else -1,
            "productType": product_type,
            "limitPrice": float(price or 0),
            "stopPrice": 0,
            "validity": "DAY",
            "disclosedQty": 0,
            "offlineOrder": False,
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

    def get_account_snapshot(self):
        self._ensure_client()

        funds = self.client.funds() or {}
        positions = self.client.positions() or {}
        orderbook = self.client.orderbook() or {}
        tradebook = self.client.tradebook() or {}
        holdings = self.client.holdings() or {}

        fund_rows = funds.get("fund_limit", []) if isinstance(funds, dict) else []

        cash = 0.0
        for row in fund_rows:
            title = str(row.get("title", "")).lower()
            if "available balance" in title:
                try:
                    cash = float(row.get("equityAmount", 0))
                    break
                except:
                    pass

        holdings_rows = holdings.get("holdings", []) if isinstance(holdings, dict) else []

        normalized_holdings = []

        for h in holdings_rows:
            item = dict(h)

            if "marketVal" in item:
                item["marketVal"] = round(float(item["marketVal"]), 2)

            if "pl" in item:
                item["pl"] = round(float(item["pl"]), 2)

            if "ltp" in item:
                item["ltp"] = round(float(item["ltp"]), 2)

            if "costPrice" in item:
                item["costPrice"] = round(float(item["costPrice"]), 2)

            normalized_holdings.append(item)

            
        holdings_value = 0.0
        unrealized = 0.0

        for h in holdings_rows:
            try:
                holdings_value += round(float(h.get("marketVal", 0)), 2)
                unrealized += round(float(h.get("pl", 0)), 2)
            except:
                pass

        equity = round(cash + holdings_value, 2)

        positions_overall = positions.get("overall", {}) if isinstance(positions, dict) else {}

        realized = round(float(positions_overall.get("pl_realized", 0)), 2)
        fees = 0.0
       
        return {
            "cash_balance": round(cash, 2),
            "realized_pnl": realized,
            "unrealized_pnl": round(unrealized, 2),
            "fees_paid": round(fees, 2),
            "equity": round(equity, 2),
            "orders": orderbook.get("orderBook", []),
            "tradebook": tradebook.get("tradeBook", []),
            "positions": positions.get("netPositions", []),
            "holdings": normalized_holdings,
            "account_source": "FYERS_LIVE",
        }
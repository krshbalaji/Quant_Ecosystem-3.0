class FyersFeed:

    def __init__(self, broker, **kwargs):
        # The high-level broker wrapper (FyersBroker instance).
        self.broker = broker

    def get_candles(self, symbol, resolution: str = "5"):
        """
        Fetch candles from the underlying FYERS client when available.
        Falls back gracefully to an empty series if history is not supported,
        allowing the rest of the system to continue running.
        """
        payload = {
            "symbol": symbol,
            "resolution": resolution,
            "date_format": "1",
            "range_from": "2026-03-05",
            "range_to": "2026-03-05",
            "cont_flag": "1",
        }

        # 1) Prefer the underlying live FYERS client if present
        live = getattr(self.broker, "live_client", None)
        client = getattr(live, "client", live)
        if client is not None and hasattr(client, "history"):
            try:
                return client.history(payload)
            except Exception:
                return {"candles": []}

        # 2) Fallback: if the broker itself exposes a history method
        if hasattr(self.broker, "history"):
            try:
                return self.broker.history(payload)
            except Exception:
                return {"candles": []}

        # 3) No history support available – return an empty structure
        return {"candles": []}
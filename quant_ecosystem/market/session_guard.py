from datetime import datetime
from zoneinfo import ZoneInfo


class SessionGuard:
    """
    Market session governance.

    Supports:
    - INDIA (NSE/BSE/MCX simplified window)
    - US (NYSE/NASDAQ simplified window)
    - CRYPTO (24x7)
    - GLOBAL FX (24x5 simplified)
    """

    def is_market_open(self, market: str, asset_class: str = "EQUITY") -> bool:
        market = (market or "").upper()
        asset_class = (asset_class or "").upper()

        if market == "CRYPTO":
            return True

        if market == "INDIA":
            return self._india_open(asset_class)

        if market == "US":
            return self._us_open(asset_class)

        if market == "GLOBAL":
            return self._global_open(asset_class)

        raise RuntimeError(f"Unsupported market: {market}")

    def _india_open(self, asset_class):
        now = datetime.now(ZoneInfo("Asia/Kolkata"))

        if now.weekday() >= 5:
            return False

        current = now.hour * 60 + now.minute

        # 09:15–15:30
        open_min = 9 * 60 + 15
        close_min = 15 * 60 + 30

        return open_min <= current <= close_min

    def _us_open(self, asset_class):
        now = datetime.now(ZoneInfo("America/New_York"))

        if now.weekday() >= 5:
            return False

        current = now.hour * 60 + now.minute

        # 09:30–16:00
        open_min = 9 * 60 + 30
        close_min = 16 * 60

        return open_min <= current <= close_min

    def _global_open(self, asset_class):
        if asset_class == "FOREX":
            now = datetime.utcnow()

            # crude 24x5
            if now.weekday() >= 5:
                return False

            return True

        return False
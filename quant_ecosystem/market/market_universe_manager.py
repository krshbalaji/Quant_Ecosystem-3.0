from datetime import datetime
from zoneinfo import ZoneInfo


import logging

logger = logging.getLogger(__name__)


class MarketUniverseManager:

    def __init__(self, config=None):
        self.config = config
        self.symbols = ["NSE:RELIANCE-EQ"]

        logger.info("MarketUniverseManager initialized")

    def get_universe(self):
        return self.symbols
        
        self._universe = {
            "stocks": ["NSE:RELIANCE-EQ", "NSE:INFY-EQ", "NSE:HDFCBANK-EQ", "NSE:SBIN-EQ"],
            "indices": ["NSE:NIFTY50-INDEX", "NSE:BANKNIFTY-INDEX"],
            "futures": ["NSE:NIFTY24MARFUT", "NSE:BANKNIFTY24MARFUT"],
            "options": ["NSE:NIFTY24MAR22000CE", "NSE:NIFTY24MAR22000PE"],
            "forex": ["FX:USDINR", "FX:EURINR"],
            "crypto": ["CRYPTO:BTCUSDT", "CRYPTO:ETHUSDT"],
            "commodities": ["MCX:GOLD", "MCX:CRUDEOIL"],
        }

    def symbols(self, asset_classes=None, regime=None, limit=10):
        chosen_classes = self._normalize_asset_classes(asset_classes)
        picked = []
        for name in chosen_classes:
            picked.extend(self._universe.get(name, []))

        if regime:
            picked = self._regime_filter(picked, str(regime).upper())

        dedup = []
        for sym in picked:
            if sym not in dedup:
                dedup.append(sym)
        return dedup[: int(limit)]

    def register(self, asset_class, symbols):
        key = str(asset_class).strip().lower()
        if key not in self._universe:
            self._universe[key] = []
        for sym in symbols:
            if sym not in self._universe[key]:
                self._universe[key].append(sym)

    def _normalize_asset_classes(self, asset_classes):
        if not asset_classes:
            return ["stocks", "indices"]
        out = []
        for item in asset_classes:
            key = str(item).strip().lower()
            if key in self._universe:
                out.append(key)
        return out or ["stocks", "indices"]

    def _regime_filter(self, symbols, regime):
        if regime in {"PANIC", "HIGH_VOLATILITY", "CRISIS"}:
            return [s for s in symbols if s.startswith("NSE:") or s.startswith("FX:") or s.startswith("CRYPTO:")]
        if regime in {"LOW_VOLATILITY", "RANGE"}:
            return [
                s
                for s in symbols
                if ("-EQ" in s) or s.endswith("INDEX") or s.startswith("FX:") or s.startswith("CRYPTO:")
            ]
        return symbols

    def asset_classes_for_session(self, now_utc=None):
        """
        Returns preferred asset classes for the current session.
        If India cash session is closed, pivots to globally active classes.
        """
        now_utc = now_utc or datetime.utcnow().replace(tzinfo=ZoneInfo("UTC"))
        ist_now = now_utc.astimezone(ZoneInfo("Asia/Kolkata"))
        weekday = ist_now.weekday()  # 0=Mon ... 6=Sun
        minutes = ist_now.hour * 60 + ist_now.minute

        india_cash_open = weekday < 5 and ((9 * 60 + 15) <= minutes <= (15 * 60 + 30))
        if india_cash_open:
            return ["stocks", "indices"]

        # India closed: keep trading alive via globally active markets.
        return ["forex", "crypto", "indices", "commodities"]

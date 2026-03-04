"""Tradable universe management for global alpha scanning."""

from __future__ import annotations

from typing import Dict, Iterable, List


class UniverseManager:
    """Maintains and filters large, multi-asset instrument universes."""

    def __init__(self):
        self._groups: Dict[str, List[str]] = {
            "nse_large_caps": ["NSE:RELIANCE-EQ", "NSE:INFY-EQ", "NSE:HDFCBANK-EQ", "NSE:SBIN-EQ"],
            "nse_mid_caps": ["NSE:TATAMOTORS-EQ", "NSE:LT-EQ", "NSE:ITC-EQ"],
            "index_futures": ["NSE:NIFTY24MARFUT", "NSE:BANKNIFTY24MARFUT"],
            "index_spot": ["NSE:NIFTY50-INDEX", "NSE:BANKNIFTY-INDEX"],
            "forex_pairs": ["FX:USDINR", "FX:EURINR", "FX:GBPUSD", "FX:USDJPY"],
            "crypto_pairs": ["CRYPTO:BTCUSDT", "CRYPTO:ETHUSDT", "CRYPTO:SOLUSDT"],
            "mcx_commodities": ["MCX:GOLD", "MCX:SILVER", "MCX:CRUDEOIL"],
            "options_index": ["NSE:NIFTY24MAR22000CE", "NSE:NIFTY24MAR22000PE"],
        }

    def load_universe(self, groups: Iterable[str] | None = None) -> List[Dict]:
        """Load symbols from selected groups as normalized instrument rows."""
        selected = list(groups) if groups else list(self._groups.keys())
        rows: List[Dict] = []
        for group in selected:
            key = str(group).strip()
            symbols = self._groups.get(key, [])
            for symbol in symbols:
                rows.append(self._to_row(symbol=symbol, group=key))
        return rows

    def update_universe(self, group: str, symbols: Iterable[str]) -> None:
        key = str(group).strip()
        if not key:
            return
        current = self._groups.setdefault(key, [])
        for symbol in symbols:
            sym = str(symbol).strip()
            if sym and sym not in current:
                current.append(sym)

    def filter_by_liquidity(self, instruments: Iterable[Dict], min_liquidity_score: float = 0.25) -> List[Dict]:
        out = []
        threshold = float(min_liquidity_score)
        for item in instruments:
            score = float(item.get("liquidity_score", item.get("default_liquidity_score", 0.5)))
            if score >= threshold:
                out.append(dict(item))
        return out

    def filter_by_volatility(
        self,
        instruments: Iterable[Dict],
        min_volatility: float = 0.01,
        max_volatility: float = 8.0,
    ) -> List[Dict]:
        out = []
        min_v = float(min_volatility)
        max_v = float(max_volatility)
        for item in instruments:
            vol = float(item.get("volatility", item.get("default_volatility", 0.3)))
            if min_v <= vol <= max_v:
                out.append(dict(item))
        return out

    def _to_row(self, symbol: str, group: str) -> Dict:
        return {
            "symbol": symbol,
            "group": group,
            "asset_class": self._asset_class(symbol),
            "default_liquidity_score": self._liquidity_seed(symbol),
            "default_volatility": self._vol_seed(symbol),
        }

    def _asset_class(self, symbol: str) -> str:
        sym = symbol.upper()
        if sym.startswith("CRYPTO:"):
            return "crypto"
        if sym.startswith("FX:"):
            return "forex"
        if sym.startswith("MCX:"):
            return "commodities"
        if sym.endswith("FUT"):
            return "futures"
        if sym.endswith("CE") or sym.endswith("PE"):
            return "options"
        if sym.endswith("INDEX"):
            return "futures"
        return "stocks"

    def _liquidity_seed(self, symbol: str) -> float:
        sym = symbol.upper()
        if sym.startswith("CRYPTO:BTC"):
            return 0.95
        if sym.startswith("FX:"):
            return 0.90
        if sym.startswith("NSE:NIFTY") or sym.startswith("NSE:BANKNIFTY"):
            return 0.88
        if sym.startswith("MCX:"):
            return 0.70
        return 0.60

    def _vol_seed(self, symbol: str) -> float:
        sym = symbol.upper()
        if sym.startswith("CRYPTO:"):
            return 1.80
        if sym.startswith("FX:"):
            return 0.35
        if sym.startswith("MCX:"):
            return 0.90
        if sym.endswith("FUT") or sym.endswith("INDEX"):
            return 0.70
        return 0.45


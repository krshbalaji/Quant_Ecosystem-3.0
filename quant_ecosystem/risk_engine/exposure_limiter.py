"""Exposure limiting logic for portfolio risk governor."""

from __future__ import annotations

from typing import Dict, Iterable, Tuple


class ExposureLimiter:
    """Applies exposure constraints at strategy, asset, and leverage levels."""

    def __init__(
        self,
        max_strategy_exposure_pct: float = 25.0,
        max_asset_exposure_pct: float = 30.0,
        total_leverage_limit: float = 1.5,
    ):
        self.max_strategy_exposure_pct = float(max_strategy_exposure_pct)
        self.max_asset_exposure_pct = float(max_asset_exposure_pct)
        self.total_leverage_limit = float(total_leverage_limit)

    def evaluate(self, state, positions: Iterable[Dict], strategy_owner_map: Dict[str, str] | None = None) -> Dict:
        strategy_owner_map = strategy_owner_map or {}
        equity = max(float(getattr(state, "equity", 0.0) or 0.0), 1e-9)

        strategy_totals: Dict[str, float] = {}
        asset_totals: Dict[str, float] = {}
        gross = 0.0
        for row in positions:
            symbol = str(row.get("symbol", "")).strip()
            notional = abs(float(row.get("notional", 0.0) or 0.0))
            strategy = str(strategy_owner_map.get(symbol, "UNKNOWN"))
            asset = self._asset_class(symbol)
            strategy_totals[strategy] = strategy_totals.get(strategy, 0.0) + notional
            asset_totals[asset] = asset_totals.get(asset, 0.0) + notional
            gross += notional

        strategy_pct = {sid: (value / equity) * 100.0 for sid, value in strategy_totals.items()}
        asset_pct = {asset: (value / equity) * 100.0 for asset, value in asset_totals.items()}
        leverage = gross / equity

        breaches = []
        for sid, pct in strategy_pct.items():
            if pct > self.max_strategy_exposure_pct:
                breaches.append(
                    {
                        "type": "STRATEGY_EXPOSURE",
                        "id": sid,
                        "exposure_pct": round(pct, 4),
                        "limit_pct": self.max_strategy_exposure_pct,
                        "action": "REDUCE_STRATEGY_EXPOSURE",
                    }
                )
        for asset, pct in asset_pct.items():
            if pct > self.max_asset_exposure_pct:
                breaches.append(
                    {
                        "type": "ASSET_EXPOSURE",
                        "asset": asset,
                        "exposure_pct": round(pct, 4),
                        "limit_pct": self.max_asset_exposure_pct,
                        "action": "REDUCE_ASSET_EXPOSURE",
                    }
                )
        if leverage > self.total_leverage_limit:
            breaches.append(
                {
                    "type": "LEVERAGE",
                    "value": round(leverage, 4),
                    "limit": self.total_leverage_limit,
                    "action": "REDUCE_LEVERAGE",
                }
            )

        return {
            "strategy_exposure_pct": {k: round(v, 4) for k, v in strategy_pct.items()},
            "asset_exposure_pct": {k: round(v, 4) for k, v in asset_pct.items()},
            "gross_leverage": round(leverage, 4),
            "breaches": breaches,
            "breached": bool(breaches),
        }

    def _asset_class(self, symbol: str) -> str:
        sym = symbol.upper()
        if sym.startswith("CRYPTO:"):
            return "CRYPTO"
        if sym.startswith("FX:"):
            return "FOREX"
        if sym.startswith("MCX:"):
            return "COMMODITY"
        if "INDEX" in sym:
            return "INDEX"
        return "EQUITY"


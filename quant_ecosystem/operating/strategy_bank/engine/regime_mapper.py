"""Regime mapping between intelligence output and strategy preferences."""

from __future__ import annotations

from typing import Dict, Iterable, List


class RegimeMapper:
    """Maps internal market regime labels to institutional tags."""

    _MAP = {
        "TREND": "TRENDING",
        "TRENDING": "TRENDING",
        "TRENDING_UP": "TRENDING",
        "TRENDING_DOWN": "TRENDING",
        "RANGE": "RANGING",
        "RANGING": "RANGING",
        "MEAN_REVERSION": "RANGING",
        "HIGH_VOL": "HIGH_VOL",
        "HIGH_VOLATILITY": "HIGH_VOL",
        "LOW_VOL": "LOW_VOL",
        "LOW_VOLATILITY": "LOW_VOL",
        "CRISIS": "CRASH",
        "PANIC": "CRASH",
        "CRASH": "CRASH",
        "BREAKOUT": "TRENDING",
    }

    def normalize(self, intelligence_report: Dict) -> str:
        source = (
            intelligence_report.get("regime_advanced")
            or intelligence_report.get("regime")
            or "RANGING"
        )
        return self._MAP.get(str(source).upper(), "RANGING")

    def enabled_for_regime(self, strategy_row: Dict, regime: str) -> bool:
        prefs = strategy_row.get("regime_preference") or []
        if not prefs:
            return True
        normalized = {self._MAP.get(str(item).upper(), str(item).upper()) for item in prefs}
        return regime in normalized

    def filter_rows(self, rows: Iterable[Dict], regime: str) -> List[Dict]:
        return [row for row in rows if self.enabled_for_regime(row, regime)]

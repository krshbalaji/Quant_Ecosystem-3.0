"""Training dataset builder for adaptive regime classification."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, List

from quant_ecosystem.regime_ai.feature_engineer import FeatureEngineer


class RegimeDatasetBuilder:
    """Creates labeled regime dataset from historical snapshots."""

    def __init__(self, feature_engineer: FeatureEngineer | None = None):
        self.feature_engineer = feature_engineer or FeatureEngineer()

    def build_dataset(self, historical_rows: Iterable[Dict]) -> List[Dict]:
        """Return list of {timestamp, features[], regime_label} rows."""
        dataset: List[Dict] = []
        for row in historical_rows:
            snapshot = dict(row.get("snapshot", row))
            extra = dict(row.get("extra_signals", {}))
            raw = self.feature_engineer.build_feature_vector(snapshot, extra_signals=extra)
            norm = self.feature_engineer.normalize_features(raw)
            label = row.get("regime_label") or self._derive_label(norm)
            dataset.append(
                {
                    "timestamp": row.get("timestamp", datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")),
                    "features": self.feature_engineer.as_ordered_vector(norm),
                    "regime_label": str(label).upper(),
                }
            )
        return dataset

    def _derive_label(self, features: Dict) -> str:
        trend = float(features.get("trend_slope", 0.0))
        vol = float(features.get("rolling_vol", 0.0))
        compression = float(features.get("range_compression", 0.0))
        vix = float(features.get("vix_norm", 0.5))

        if vol > 0.85 or vix > 0.85:
            if trend < -0.3:
                return "CRASH_EVENT"
            return "HIGH_VOLATILITY"
        if abs(trend) > 0.45 and vol < 0.8:
            return "TRENDING_BULL" if trend > 0 else "TRENDING_BEAR"
        if vol < 0.25 and abs(trend) < 0.2:
            return "LOW_VOLATILITY"
        if compression > 0.5:
            return "RANGE_BOUND"
        return "RANGE_BOUND"


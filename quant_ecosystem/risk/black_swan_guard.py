class BlackSwanGuard:

    def evaluate(self, intelligence_report, snapshots=None):
        snapshots = snapshots or []
        vol = float(intelligence_report.get("volatility", 0.0))
        trend = float(intelligence_report.get("trend", 0.0))
        regime = str(intelligence_report.get("regime", "")).upper()

        spread_stress = 0.0
        for snap in snapshots:
            closes = snap.get("close", [])
            if len(closes) < 2:
                continue
            c0 = float(closes[-2])
            c1 = float(closes[-1])
            if c0 > 0:
                spread_stress = max(spread_stress, abs((c1 - c0) / c0) * 100.0)

        if regime in {"CRISIS", "PANIC"} or vol >= 2.8:
            return {"action": "CLOSE_EXPOSURE", "reason": "EXTREME_VOLATILITY_OR_PANIC"}
        if spread_stress >= 1.2:
            return {"action": "PAUSE", "reason": "ABNORMAL_SPREAD"}
        if vol >= 1.8 and trend < 0:
            return {"action": "REDUCE_RISK", "reason": "INDEX_STRESS_DOWNTREND"}
        return {"action": "NORMAL", "reason": "NO_BLACK_SWAN_SIGNAL"}

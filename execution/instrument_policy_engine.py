class InstrumentPolicyEngine:

    def select(self, candidates, regime, trade_type):
        if not candidates:
            return None

        ranked = []
        for candidate in candidates:
            score = self._score_candidate(candidate, regime, trade_type)
            item = dict(candidate)
            item["instrument_score"] = round(score, 6)
            ranked.append(item)

        ranked.sort(key=lambda x: x["instrument_score"], reverse=True)
        return ranked[0]

    def _score_candidate(self, candidate, regime, trade_type):
        confidence = float(candidate.get("confidence", 0.0))
        volatility = float(candidate.get("volatility", 0.0))
        trend = float(candidate.get("trend", 0.0))
        side = str(candidate.get("side", "HOLD")).upper()
        symbol = str(candidate.get("symbol", "")).upper()

        score = confidence

        if regime == "TREND":
            if (side == "BUY" and trend > 0) or (side == "SELL" and trend < 0):
                score += 0.12
        elif regime == "MEAN_REVERSION":
            if (side == "BUY" and trend < 0) or (side == "SELL" and trend > 0):
                score += 0.10
        elif regime == "HIGH_VOLATILITY":
            score -= max(0.0, volatility - 1.4) * 0.05
        elif regime == "LOW_VOLATILITY":
            score += max(0.0, 0.7 - volatility) * 0.06
        elif regime == "CRISIS":
            score -= 0.25

        # Liquidity proxy by instrument family naming pattern.
        if "NIFTY" in symbol or "BANKNIFTY" in symbol or "RELIANCE" in symbol:
            score += 0.04

        if trade_type == "SCALP":
            score += 0.03 if volatility > 0.25 else -0.02
        elif trade_type == "SWING":
            score += 0.03 if abs(trend) > 0 else -0.01

        return score

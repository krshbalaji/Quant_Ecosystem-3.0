class StrategyPortfolioManager:

    def __init__(self, correlation_threshold=0.75):
        self.correlation_threshold = float(correlation_threshold)

    def build_portfolio(self, strategy_reports):
        ranked = sorted(strategy_reports, key=lambda item: float(item.get("score", 0.0)), reverse=True)
        selected = []
        disabled = []
        active_reports = []

        for report in ranked:
            stage = str(report.get("stage", "")).lower()
            if stage not in {"paper", "shadow", "live"}:
                active_reports.append({**report, "active": False, "allocation_pct": 0.0})
                continue

            if report.get("disabled_by_correlation", False):
                disabled.append({"id": report.get("id"), "reason": "CORRELATION"})
                active_reports.append({**report, "active": False, "allocation_pct": 0.0})
                continue

            corr_penalty = float(report.get("correlation_penalty", 0.0))
            if corr_penalty >= (self.correlation_threshold * 20.0):
                disabled.append({"id": report.get("id"), "reason": "CORRELATION_PENALTY"})
                active_reports.append({**report, "active": False, "allocation_pct": 0.0})
                continue

            selected.append(report)

        allocations = self._allocation_plan(selected)
        allocation_map = {item["id"]: item["allocation_pct"] for item in allocations}

        final_reports = []
        for report in active_reports + selected:
            allocation_pct = float(allocation_map.get(report.get("id"), 0.0))
            final_reports.append({**report, "active": allocation_pct > 0, "allocation_pct": allocation_pct})

        final_reports.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)
        return {
            "reports": final_reports,
            "allocations": allocations,
            "disabled": disabled,
            "active_ids": [item["id"] for item in allocations if item["allocation_pct"] > 0],
        }

    def _allocation_plan(self, selected):
        if not selected:
            return []
        score_sum = sum(max(float(item.get("score", 0.0)), 0.01) for item in selected)
        out = []
        for item in selected:
            weight = max(float(item.get("score", 0.0)), 0.01) / score_sum
            allocation = min(30.0, round(weight * 100.0, 2))
            out.append({"id": item["id"], "allocation_pct": allocation})
        total = sum(item["allocation_pct"] for item in out)
        if total > 0:
            scale = 100.0 / total
            for item in out:
                item["allocation_pct"] = round(item["allocation_pct"] * scale, 2)
        return out

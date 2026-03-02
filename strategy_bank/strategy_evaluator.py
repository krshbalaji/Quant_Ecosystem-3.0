from core.config_loader import Config
from research.backtest.backtest_engine import BacktestEngine
from strategy_bank.correlation_engine import CorrelationEngine
from strategy_bank.lifecycle_manager import StrategyLifecycleManager
from strategy_bank.strategy_scorer import StrategyScorer


class StrategyEvaluator:

    def __init__(self):
        self.config = Config()
        self.backtest = BacktestEngine()
        self.scorer = StrategyScorer()
        self.lifecycle = StrategyLifecycleManager()
        self.correlation = CorrelationEngine()

    def evaluate(self, strategies):
        reports = []
        for strategy in strategies:
            metrics = self.backtest.run(strategy["callable"])
            reports.append(
                {
                    "id": strategy["id"],
                    "name": strategy["name"],
                    "metrics": metrics,
                    "score": 0.0,
                    "stage": "REJECTED",
                    "correlation_penalty": 0.0,
                    "disabled_by_correlation": False,
                }
            )

        matrix = self.correlation.correlation_matrix(reports)
        correlated_pairs = self.correlation.correlated_pairs(
            matrix=matrix,
            threshold=self.config.diversification_correlation_threshold,
        )

        penalty_map = {}
        for left, right, corr in correlated_pairs:
            penalty = abs(corr) * 20.0
            penalty_map[left] = penalty_map.get(left, 0.0) + penalty
            penalty_map[right] = penalty_map.get(right, 0.0) + penalty

        reports.sort(key=lambda item: item["metrics"].get("expectancy_rolling_100", 0.0), reverse=True)
        selected = set()
        for report in reports:
            report_id = report["id"]
            report["correlation_penalty"] = round(penalty_map.get(report_id, 0.0), 4)
            report["score"] = self.scorer.score(
                report["metrics"],
                correlation_penalty=report["correlation_penalty"],
            )

            too_correlated = False
            for selected_id in selected:
                corr = abs(matrix.get(report_id, {}).get(selected_id, 0.0))
                if corr >= self.config.diversification_correlation_threshold:
                    too_correlated = True
                    break

            report["disabled_by_correlation"] = too_correlated
            if not too_correlated:
                selected.add(report_id)

            if too_correlated:
                report["stage"] = "REJECTED"
            else:
                report["stage"] = self.lifecycle.promote(report["metrics"])

        reports.sort(key=lambda item: item["score"], reverse=True)

        active = [item for item in reports if item.get("stage") in {"PAPER", "LIVE"}]
        if not active and self.config.mode.upper() == "PAPER" and self.config.allow_paper_shadow and reports:
            for report in reports:
                if report.get("disabled_by_correlation"):
                    continue
                report["stage"] = "PAPER_SHADOW"
                break

        return reports

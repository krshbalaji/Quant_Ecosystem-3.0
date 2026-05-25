class WalkForwardEngine:

    def split(
        self,
        series,
        train_ratio=0.7,
    ):
        split_idx = int(
            len(series) * train_ratio
        )

        return (
            series[:split_idx],
            series[split_idx:],
        )

    def rolling_windows(
        self,
        series,
        train_size=20,
        test_size=10,
    ):
        windows = []

        start = 0

        while (
            start
            + train_size
            + test_size
        ) <= len(series):
            train = series[
                start : start + train_size
            ]

            test = series[
                start + train_size :
                start + train_size + test_size
            ]

            windows.append(
                {
                    "train": train,
                    "test": test,
                }
            )

            start += test_size

        return windows

    def robustness_snapshot(
        self,
        window_results,
    ):
        if not window_results:
            return {
                "windows": 0,
                "avg_score": 0.0,
                "best_score": 0.0,
                "worst_score": 0.0,
            }

        scores = [
            x["score"]
            for x in window_results
        ]

        return {
            "windows": len(scores),
            "avg_score": (
                sum(scores)
                / len(scores)
            ),
            "best_score": max(scores),
            "worst_score": min(scores),
        }

    def run(
        self,
        series,
        scorer,
        train_size=20,
        test_size=10,
    ):
        windows = self.rolling_windows(
            series,
            train_size=train_size,
            test_size=test_size,
        )

        results = []

        for window in windows:
            score = scorer(
                window["train"],
                window["test"],
            )

            results.append(
                {
                    "train_len": len(
                        window["train"]
                    ),
                    "test_len": len(
                        window["test"]
                    ),
                    "score": score,
                }
            )

        snapshot = (
            self.robustness_snapshot(
                results
            )
        )

        return {
            "results": results,
            "snapshot": snapshot,
        }


walkforward_engine = (
    WalkForwardEngine()
)
class ResearchBacktestHarness:

    def replay(
        self,
        signal_events,
    ):
        results = []

        for event in signal_events:
            entry = float(
                event["entry_price"]
            )

            exit_price = float(
                event["exit_price"]
            )

            direction = event.get(
                "direction",
                "LONG",
            )

            if direction == "LONG":
                pnl = exit_price - entry
            else:
                pnl = entry - exit_price

            results.append(
                {
                    "symbol": event["symbol"],
                    "direction": direction,
                    "entry_price": entry,
                    "exit_price": exit_price,
                    "pnl": pnl,
                }
            )

        return results

    def performance_snapshot(
        self,
        replay_results,
    ):
        if not replay_results:
            return {
                "trades": 0,
                "wins": 0,
                "losses": 0,
                "total_pnl": 0.0,
                "win_rate": 0.0,
            }

        wins = [
            x for x in replay_results
            if x["pnl"] > 0
        ]

        losses = [
            x for x in replay_results
            if x["pnl"] <= 0
        ]

        total_pnl = sum(
            x["pnl"]
            for x in replay_results
        )

        return {
            "trades": len(replay_results),
            "wins": len(wins),
            "losses": len(losses),
            "total_pnl": total_pnl,
            "win_rate": (
                len(wins)
                / len(replay_results)
            ) * 100.0,
        }

    def run(
        self,
        signal_events,
    ):
        replay_results = self.replay(
            signal_events
        )

        snapshot = (
            self.performance_snapshot(
                replay_results
            )
        )

        return {
            "replay_results": replay_results,
            "snapshot": snapshot,
        }


research_backtest_harness = (
    ResearchBacktestHarness()
)
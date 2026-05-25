class DrawdownGuardian:

    def evaluate(
        self,
        total_pnl,
        peak_equity,
        current_equity,
        max_drawdown_limit=10000,
    ):
        drawdown = (
            peak_equity
            - current_equity
        )

        if drawdown >= max_drawdown_limit:
            action = "HALT"

        elif total_pnl < 0:
            action = "WATCH"

        else:
            action = "NORMAL"

        return {
            "drawdown": drawdown,
            "action": action,
        }

    def strategy_guard(
        self,
        snapshot,
        max_loss_limit=5000,
    ):
        if snapshot["total_pnl"] <= (
            -max_loss_limit
        ):
            return {
                "strategy_id": (
                    snapshot["strategy_id"]
                ),
                "action": "DISABLE",
            }

        return {
            "strategy_id": (
                snapshot["strategy_id"]
            ),
            "action": "ALLOW",
        }


drawdown_guardian = (
    DrawdownGuardian()
)
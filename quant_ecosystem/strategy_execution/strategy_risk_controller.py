from quant_ecosystem.strategy import (
    strategy_lifecycle,
)

from quant_ecosystem.strategy_execution import (
    StrategyRiskBudget,
)


class StrategyRiskController:

    def __init__(self):
        self._budgets = {}
        self._reject_streaks = {}
        self._kill_switches = {}

    def register_budget(
        self,
        budget: StrategyRiskBudget,
    ):
        self._budgets[
            budget.strategy_id
        ] = budget

        return budget

    def get_budget(
        self,
        strategy_id,
    ):
        return self._budgets.get(strategy_id)

    def clear(self):
        self._budgets.clear()
        self._reject_streaks.clear()
        self._kill_switches.clear()

    def enable_kill_switch(
        self,
        strategy_id,
    ):
        self._kill_switches[
            strategy_id
        ] = True

        strategy_lifecycle.suspend(
            strategy_id
        )

    def disable_kill_switch(
        self,
        strategy_id,
    ):
        self._kill_switches.pop(
            strategy_id,
            None,
        )

    def kill_switch_active(
        self,
        strategy_id,
    ):
        return self._kill_switches.get(
            strategy_id,
            False,
        )

    def record_reject(
        self,
        strategy_id,
        threshold=3,
    ):
        current = self._reject_streaks.get(
            strategy_id,
            0,
        )

        current += 1

        self._reject_streaks[
            strategy_id
        ] = current

        if current >= threshold:
            strategy_lifecycle.pause(
                strategy_id
            )

    def reset_rejects(
        self,
        strategy_id,
    ):
        self._reject_streaks.pop(
            strategy_id,
            None,
        )

    def validate(
        self,
        strategy_id,
        proposed_notional=0.0,
    ):
        if self.kill_switch_active(
            strategy_id
        ):
            return (
                False,
                "STRATEGY_KILL_SWITCH",
            )

        if not strategy_lifecycle.is_trade_allowed(
            strategy_id
        ):
            return (
                False,
                "STRATEGY_DISABLED",
            )

        budget = self.get_budget(
            strategy_id
        )

        if not budget:
            return (
                True,
                "OK",
            )

        if (
            budget.max_capital > 0
            and proposed_notional
            > budget.remaining_capital
        ):
            return (
                False,
                "STRATEGY_CAPITAL_LIMIT",
            )

        if (
            budget.max_positions > 0
            and budget.current_positions
            >= budget.max_positions
        ):
            return (
                False,
                "STRATEGY_POSITION_LIMIT",
            )

        if (
            budget.max_loss > 0
            and abs(budget.total_pnl)
            >= budget.max_loss
        ):
            return (
                False,
                "STRATEGY_MAX_LOSS",
            )

        return (
            True,
            "OK",
        )


strategy_risk_controller = (
    StrategyRiskController()
)
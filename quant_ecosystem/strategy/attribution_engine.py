import math


class AttributionEngine:

    def strategy_pnl(
        self,
        trades,
    ):
        return sum(
            float(t.get("pnl", 0.0))
            for t in trades
        )

    def win_rate(
        self,
        trades,
    ):
        if not trades:
            return 0.0

        wins = sum(
            1
            for t in trades
            if float(t.get("pnl", 0.0)) > 0
        )

        return (
            wins / len(trades)
        ) * 100.0

    def expectancy(
        self,
        trades,
    ):
        if not trades:
            return 0.0

        wins = [
            float(t.get("pnl", 0.0))
            for t in trades
            if float(t.get("pnl", 0.0)) > 0
        ]

        losses = [
            float(t.get("pnl", 0.0))
            for t in trades
            if float(t.get("pnl", 0.0)) < 0
        ]

        avg_win = (
            sum(wins) / len(wins)
            if wins else 0.0
        )

        avg_loss = (
            sum(losses) / len(losses)
            if losses else 0.0
        )

        wr = self.win_rate(trades) / 100.0
        lr = 1.0 - wr

        return (
            (wr * avg_win)
            + (lr * avg_loss)
        )

    def average_win(
        self,
        trades,
    ):
        wins = [
            float(t.get("pnl", 0.0))
            for t in trades
            if float(t.get("pnl", 0.0)) > 0
        ]

        if not wins:
            return 0.0

        return sum(wins) / len(wins)

    def average_loss(
        self,
        trades,
    ):
        losses = [
            float(t.get("pnl", 0.0))
            for t in trades
            if float(t.get("pnl", 0.0)) < 0
        ]

        if not losses:
            return 0.0

        return sum(losses) / len(losses)

    def max_drawdown(
        self,
        equity_curve,
    ):
        if not equity_curve:
            return 0.0

        peak = equity_curve[0]
        max_dd = 0.0

        for value in equity_curve:
            if value > peak:
                peak = value

            dd = (
                (peak - value)
                / peak
            ) if peak > 0 else 0.0

            max_dd = max(
                max_dd,
                dd,
            )

        return max_dd

    def sharpe_proxy(
        self,
        returns,
    ):
        if len(returns) < 2:
            return 0.0

        mean = (
            sum(returns)
            / len(returns)
        )

        variance = sum(
            (r - mean) ** 2
            for r in returns
        ) / (len(returns) - 1)

        std = math.sqrt(variance)

        if std == 0:
            return 0.0

        return mean / std

    def contribution_pct(
        self,
        strategy_pnl,
        total_pnl,
    ):
        if total_pnl == 0:
            return 0.0

        return (
            float(strategy_pnl)
            / float(total_pnl)
        ) * 100.0

    def strategy_summary(
        self,
        trades,
        equity_curve=None,
        returns=None,
        total_system_pnl=None,
    ):
        pnl = self.strategy_pnl(trades)

        return {
            "pnl": pnl,
            "win_rate": self.win_rate(trades),
            "expectancy": self.expectancy(trades),
            "avg_win": self.average_win(trades),
            "avg_loss": self.average_loss(trades),
            "max_drawdown": self.max_drawdown(
                equity_curve or []
            ),
            "sharpe_proxy": self.sharpe_proxy(
                returns or []
            ),
            "contribution_pct": self.contribution_pct(
                pnl,
                total_system_pnl or pnl,
            ),
        }


attribution_engine = AttributionEngine()
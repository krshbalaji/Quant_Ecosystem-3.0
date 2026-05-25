import math


class PortfolioPerformanceAnalytics:

    def cumulative_return(
        self,
        equity_curve,
    ):
        if not equity_curve or len(equity_curve) < 2:
            return 0.0

        start = float(equity_curve[0])
        end = float(equity_curve[-1])

        if start == 0:
            return 0.0

        return ((end - start) / start) * 100.0

    def cagr(
        self,
        equity_curve,
        periods_per_year=252,
    ):
        if not equity_curve or len(equity_curve) < 2:
            return 0.0

        start = float(equity_curve[0])
        end = float(equity_curve[-1])

        if start <= 0:
            return 0.0

        years = len(equity_curve) / periods_per_year

        if years <= 0:
            return 0.0

        return (
            ((end / start) ** (1 / years)) - 1
        ) * 100.0

    def returns_series(
        self,
        equity_curve,
    ):
        if not equity_curve or len(equity_curve) < 2:
            return []

        returns = []

        for i in range(1, len(equity_curve)):
            prev = float(equity_curve[i - 1])
            curr = float(equity_curve[i])

            if prev == 0:
                continue

            returns.append(
                (curr - prev) / prev
            )

        return returns

    def sharpe_ratio(
        self,
        equity_curve,
        risk_free_rate=0.0,
        periods_per_year=252,
    ):
        returns = self.returns_series(
            equity_curve
        )

        if not returns:
            return 0.0

        mean_return = (
            sum(returns) / len(returns)
        )

        variance = sum(
            (r - mean_return) ** 2
            for r in returns
        ) / len(returns)

        std_dev = math.sqrt(variance)

        if std_dev == 0:
            return 0.0

        annualized_return = (
            mean_return * periods_per_year
        )

        annualized_std = (
            std_dev * math.sqrt(periods_per_year)
        )

        return (
            annualized_return - risk_free_rate
        ) / annualized_std

    def sortino_ratio(
        self,
        equity_curve,
        risk_free_rate=0.0,
        periods_per_year=252,
    ):
        returns = self.returns_series(
            equity_curve
        )

        if not returns:
            return 0.0

        downside = [
            r for r in returns if r < 0
        ]

        if not downside:
            return 0.0

        mean_return = (
            sum(returns) / len(returns)
        )

        downside_variance = sum(
            r ** 2 for r in downside
        ) / len(downside)

        downside_std = math.sqrt(
            downside_variance
        )

        if downside_std == 0:
            return 0.0

        annualized_return = (
            mean_return * periods_per_year
        )

        annualized_downside = (
            downside_std
            * math.sqrt(periods_per_year)
        )

        return (
            annualized_return - risk_free_rate
        ) / annualized_downside

    def max_drawdown(
        self,
        equity_curve,
    ):
        if not equity_curve:
            return 0.0

        peak = float(equity_curve[0])
        max_dd = 0.0

        for value in equity_curve:
            value = float(value)

            if value > peak:
                peak = value

            dd = ((peak - value) / peak) * 100.0

            if dd > max_dd:
                max_dd = dd

        return max_dd

    def expectancy(
        self,
        trade_pnls,
    ):
        if not trade_pnls:
            return 0.0

        wins = [
            x for x in trade_pnls if x > 0
        ]

        losses = [
            x for x in trade_pnls if x < 0
        ]

        total = len(trade_pnls)

        if total == 0:
            return 0.0

        win_rate = len(wins) / total
        loss_rate = len(losses) / total

        avg_win = (
            sum(wins) / len(wins)
            if wins else 0.0
        )

        avg_loss = abs(
            sum(losses) / len(losses)
        ) if losses else 0.0

        return (
            (win_rate * avg_win)
            - (loss_rate * avg_loss)
        )

    def win_rate(
        self,
        trade_pnls,
    ):
        if not trade_pnls:
            return 0.0

        wins = len(
            [x for x in trade_pnls if x > 0]
        )

        return (
            wins / len(trade_pnls)
        ) * 100.0

    def profit_factor(
        self,
        trade_pnls,
    ):
        if not trade_pnls:
            return 0.0

        gross_profit = sum(
            x for x in trade_pnls if x > 0
        )

        gross_loss = abs(sum(
            x for x in trade_pnls if x < 0
        ))

        if gross_loss == 0:
            return 0.0

        return gross_profit / gross_loss


portfolio_performance_analytics = (
    PortfolioPerformanceAnalytics()
)
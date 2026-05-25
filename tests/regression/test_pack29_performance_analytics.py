from quant_ecosystem.portfolio.performance_analytics import (
    portfolio_performance_analytics,
)


def test_cumulative_return():
    result = (
        portfolio_performance_analytics
        .cumulative_return(
            [100000, 110000]
        )
    )

    assert result == 10.0


def test_max_drawdown():
    result = (
        portfolio_performance_analytics
        .max_drawdown(
            [100, 120, 90, 130]
        )
    )

    assert result == 25.0


def test_win_rate():
    result = (
        portfolio_performance_analytics
        .win_rate(
            [100, -50, 200]
        )
    )

    assert result == (
        2 / 3
    ) * 100.0


def test_profit_factor():
    result = (
        portfolio_performance_analytics
        .profit_factor(
            [100, -50, 200]
        )
    )

    assert result == 6.0


def test_expectancy():
    result = (
        portfolio_performance_analytics
        .expectancy(
            [100, -50, 200]
        )
    )

    assert result > 0
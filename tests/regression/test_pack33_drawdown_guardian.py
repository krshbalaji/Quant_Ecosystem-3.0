from quant_ecosystem.monitoring.drawdown_guardian import (
    drawdown_guardian,
)


def test_guardian_halt():
    result = (
        drawdown_guardian
        .evaluate(
            total_pnl=-12000,
            peak_equity=100000,
            current_equity=85000,
        )
    )

    assert result["action"] == "HALT"


def test_strategy_disable():
    result = (
        drawdown_guardian
        .strategy_guard(
            {
                "strategy_id": "alpha_1",
                "total_pnl": -6000,
            }
        )
    )

    assert result["action"] == "DISABLE"
from quant_ecosystem.autonomous_research import (
    autonomous_research_loop_controller,
    research_memory,
    alpha_evolution_memory,
)


def setup_function():
    research_memory.clear()
    alpha_evolution_memory.clear()


def test_basic_evaluation():
    result = (
        autonomous_research_loop_controller
        .evaluate_signal(
            "sig1",
            "strat1",
            80,
            2,
        )
    )

    assert result["retire"] is False


def test_retire_path():
    result = (
        autonomous_research_loop_controller
        .evaluate_signal(
            "sig2",
            "strat2",
            40,
            20,
        )
    )

    assert result["retire"] is True


def test_prior_signal_lookup():
    research_memory.record(
        "sig3",
        75,
        "WIN",
    )

    result = (
        autonomous_research_loop_controller
        .evaluate_signal(
            "sig3",
            "strat3",
            70,
            1,
        )
    )

    assert result["prior_signal"] is not None


def test_strategy_history():
    alpha_evolution_memory.record(
        "strat4",
        75,
        2.0,
        12000,
    )

    result = (
        autonomous_research_loop_controller
        .evaluate_signal(
            "sig4",
            "strat4",
            90,
            1,
        )
    )

    assert result["strategy_history"] is not None


def test_priority_high():
    result = (
        autonomous_research_loop_controller
        .evaluate_signal(
            "sig5",
            "strat5",
            95,
            1,
            base_weight=1.0,
            win_rate=85,
        )
    )

    assert result["priority"] == "HIGH"


def test_priority_normal():
    result = (
        autonomous_research_loop_controller
        .evaluate_signal(
            "sig6",
            "strat6",
            30,
            10,
            base_weight=1.0,
            win_rate=30,
        )
    )

    assert result["priority"] == "NORMAL"
from quant_ecosystem.autonomous_research import (
    adaptive_weight_engine,
    alpha_evolution_memory,
)


def setup_function():
    alpha_evolution_memory.clear()


def test_weight_strong():
    result = (
        adaptive_weight_engine.adjust_weight(
            1.0,
            80,
            90,
        )
    )

    assert result > 1.0


def test_weight_weak():
    result = (
        adaptive_weight_engine.adjust_weight(
            1.0,
            20,
            20,
        )
    )

    assert result < 1.0


def test_record():
    alpha_evolution_memory.record(
        "s1",
        70,
        2.1,
        10000,
    )

    result = (
        alpha_evolution_memory.fetch("s1")
    )

    assert result is not None


def test_rank():
    alpha_evolution_memory.record(
        "s1",
        60,
        1.5,
        1000,
    )

    alpha_evolution_memory.record(
        "s2",
        75,
        2.5,
        4000,
    )

    ranked = (
        alpha_evolution_memory.rank()
    )

    assert ranked[0][0] == "s2"


def test_clear():
    alpha_evolution_memory.record(
        "x",
        1,
        1,
        1,
    )

    alpha_evolution_memory.clear()

    assert (
        alpha_evolution_memory.fetch("x")
        is None
    )
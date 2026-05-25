from quant_ecosystem.workflow import (
    workflow_engine,
    retry_controller,
)


def test_workflow_success():
    def step1():
        return 1

    def step2():
        return 2

    result = workflow_engine.execute(
        [step1, step2]
    )

    assert result["success"] is True
    assert result["results"] == [1, 2]


def test_workflow_failure():
    def step1():
        return 1

    def step2():
        raise ValueError()

    result = workflow_engine.execute(
        [step1, step2]
    )

    assert result["success"] is False


def test_retry_success():
    state = {"count": 0}

    def flaky():
        state["count"] += 1

        if state["count"] < 2:
            raise ValueError()

        return "OK"

    result = retry_controller.execute(
        flaky
    )

    assert result == "OK"


def test_retry_failure():
    def bad():
        raise RuntimeError()

    try:
        retry_controller.execute(
            bad,
            retries=2,
        )
        assert False
    except RuntimeError:
        assert True


def test_compensation():
    called = []

    def bad():
        raise ValueError()

    def rollback():
        called.append(True)

    workflow_engine.execute(
        [bad],
        compensations=[rollback],
    )

    assert len(called) == 1
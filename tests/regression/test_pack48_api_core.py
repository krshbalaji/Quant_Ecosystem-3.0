from quant_ecosystem.api import (
    api_router,
)
from quant_ecosystem.runtime import (
    lifecycle_manager,
)


def setup_function():
    lifecycle_manager.stop()


def test_health():
    result = api_router.route(
        "health"
    )

    assert result["status"] == "HEALTHY"


def test_runtime_start():
    result = api_router.route(
        "runtime",
        action="start",
    )

    assert result == "RUNNING"


def test_runtime_stop():
    api_router.route(
        "runtime",
        action="start",
    )

    result = api_router.route(
        "runtime",
        action="stop",
    )

    assert result == "STOPPED"


def test_execution_submit():
    result = api_router.route(
        "execution",
        payload={"symbol": "INFY"},
    )

    assert result["accepted"] is True


def test_unknown():
    try:
        api_router.route("broken")
        assert False
    except ValueError:
        assert True
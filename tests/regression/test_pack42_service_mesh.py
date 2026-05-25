from quant_ecosystem.integration import (
    service_container,
    service_mesh,
    orchestration_router,
    composition_engine,
)


class DemoService:

    def ping(self):
        return "PONG"

    def add(
        self,
        a,
        b,
    ):
        return a + b


def setup_function():
    service_container.clear()


def test_mesh_call():
    service_container.register(
        "demo",
        DemoService(),
    )

    result = service_mesh.call(
        "demo",
        "ping",
    )

    assert result == "PONG"


def test_router():
    service_container.register(
        "demo",
        DemoService(),
    )

    result = orchestration_router.route(
        "demo",
        "add",
        2,
        3,
    )

    assert result == 5


def test_compose():
    result = composition_engine.compose(
        {
            "demo": DemoService(),
        }
    )

    assert result is True


def test_missing_service():
    try:
        service_mesh.call(
            "missing",
            "ping",
        )
        assert False
    except ValueError:
        assert True


def test_registered_after_compose():
    composition_engine.compose(
        {
            "demo": DemoService(),
        }
    )

    result = service_mesh.call(
        "demo",
        "ping",
    )

    assert result == "PONG"
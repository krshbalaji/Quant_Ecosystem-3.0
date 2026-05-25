from quant_ecosystem.integration import (
    service_container,
    dependency_injector,
    service_registry,
)


def setup_function():
    service_container.clear()


def test_register():
    service_container.register(
        "risk",
        object(),
    )

    assert service_container.exists(
        "risk"
    )


def test_resolve():
    svc = object()

    service_container.register(
        "exec",
        svc,
    )

    assert (
        dependency_injector.inject(
            "exec"
        )
        is svc
    )


def test_batch_register():
    service_registry.register_batch(
        {
            "a": object(),
            "b": object(),
        }
    )

    assert len(
        service_registry.registered()
    ) == 2


def test_missing():
    assert (
        dependency_injector.inject(
            "missing"
        )
        is None
    )


def test_clear():
    service_container.register(
        "x",
        object(),
    )

    service_container.clear()

    assert (
        service_container.exists("x")
        is False
    )
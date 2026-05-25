from quant_ecosystem.governance.model_registry import (
    model_registry,
)


def setup_function():
    model_registry._models.clear()


def test_register():
    result = (
        model_registry.register(
            "alpha_model",
            "v1",
            "RESEARCH",
        )
    )

    assert result["active"] is True


def test_get():
    model_registry.register(
        "alpha_model",
        "v1",
        "RESEARCH",
    )

    result = model_registry.get(
        "alpha_model",
        "v1",
    )

    assert result["version"] == "v1"


def test_deactivate():
    model_registry.register(
        "alpha_model",
        "v1",
        "RESEARCH",
    )

    model_registry.deactivate(
        "alpha_model",
        "v1",
    )

    result = model_registry.get(
        "alpha_model",
        "v1",
    )

    assert result["active"] is False


def test_active_models():
    model_registry.register(
        "m1",
        "v1",
        "RESEARCH",
    )

    assert len(
        model_registry.active_models()
    ) == 1
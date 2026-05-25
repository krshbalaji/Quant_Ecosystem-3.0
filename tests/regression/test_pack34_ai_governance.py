from quant_ecosystem.governance import (
    ai_governance,
    model_registry,
)


def setup_function():
    model_registry._models.clear()


def test_missing_model():
    result = (
        ai_governance.evaluate(
            None,
            {},
        )
    )

    assert result["approved"] is False


def test_inactive_model():
    model = (
        model_registry.register(
            "alpha",
            "v1",
            "RESEARCH",
        )
    )

    model_registry.deactivate(
        "alpha",
        "v1",
    )

    result = (
        ai_governance.evaluate(
            model,
            {},
        )
    )

    assert result["approved"] is False


def test_approved():
    model = (
        model_registry.register(
            "alpha",
            "v1",
            "RESEARCH",
        )
    )

    result = (
        ai_governance.evaluate(
            model,
            {},
        )
    )

    assert result["approved"] is True


def test_policy_block():
    model = (
        model_registry.register(
            "alpha",
            "v1",
            "RESEARCH",
        )
    )

    result = (
        ai_governance.evaluate(
            model,
            {
                "risk_level":
                "PROHIBITED"
            },
        )
    )

    assert result["approved"] is False
from quant_ecosystem.security import (
    token_validator,
    permission_engine,
    access_controller,
    secrets_vault,
)


def setup_function():
    secrets_vault.clear()


def test_token_valid():
    assert token_validator.validate(
        "QE3_SECURE_TOKEN"
    ) is True


def test_permission():
    assert permission_engine.allowed(
        "admin",
        "trade",
    ) is True


def test_access_authorized():
    assert access_controller.authorize(
        "QE3_SECURE_TOKEN",
        "admin",
        "trade",
    ) is True


def test_access_denied():
    assert access_controller.authorize(
        "BAD",
        "admin",
        "trade",
    ) is False


def test_secret_store():
    secrets_vault.store(
        "broker_key",
        "abc123",
    )

    assert (
        secrets_vault.fetch(
            "broker_key"
        )
        == "abc123"
    )
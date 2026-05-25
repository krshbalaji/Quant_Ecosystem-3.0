from quant_ecosystem.api import (
    api_router,
)


def test_governance_authorized():
    result = api_router.route(
        "governance",
        payload={
            "token": "QE3_SECURE_TOKEN",
            "role": "admin",
            "action": "trade",
        },
    )

    assert result is True


def test_governance_denied():
    result = api_router.route(
        "governance",
        payload={
            "token": "BAD",
            "role": "admin",
            "action": "trade",
        },
    )

    assert result is False


def test_orchestration():
    def step1():
        return 10

    def step2():
        return 20

    result = api_router.route(
        "orchestration",
        payload={
            "steps": [step1, step2]
        },
    )

    assert result["success"] is True
    assert result["results"] == [10, 20]


def test_api_contract():
    from quant_ecosystem.api import ApiRequest

    req = ApiRequest(
        endpoint="health"
    )

    assert req.endpoint == "health"


def test_unknown_still_fails():
    try:
        api_router.route("unknown")
        assert False
    except ValueError:
        assert True
from quant_ecosystem.execution.dispatch.execution_dispatcher import (
    ExecutionDispatcher,
)


class DummyLive:
    def execute(self, **kwargs):
        return {"id": "LIVE"}


class DummyPaper:
    def execute(self, **kwargs):
        return {"id": "PAPER"}


class Caps:
    supports_retry = True


class NoRetryCaps:
    supports_retry = False


class Broker:
    def place_order(self, **kwargs):
        return {"id": "RAW"}


def test_dispatch_live():
    d = ExecutionDispatcher(
        DummyLive(),
        DummyPaper(),
    )

    result = d.dispatch(
        mode="LIVE",
        broker=Broker(),
        broker_name="x",
        normalized_symbol="INFY",
        symbol="INFY",
        side="BUY",
        qty=1,
        price=100,
        fee=0,
        meta={},
        asset_class="EQUITY",
        caps=Caps(),
    )

    assert result["id"] == "LIVE"


def test_dispatch_paper():
    d = ExecutionDispatcher(
        DummyLive(),
        DummyPaper(),
    )

    result = d.dispatch(
        mode="PAPER",
        broker=Broker(),
        broker_name="x",
        normalized_symbol="INFY",
        symbol="INFY",
        side="BUY",
        qty=1,
        price=100,
        fee=0,
        meta={},
        asset_class="EQUITY",
        caps=Caps(),
    )

    assert result["id"] == "PAPER"
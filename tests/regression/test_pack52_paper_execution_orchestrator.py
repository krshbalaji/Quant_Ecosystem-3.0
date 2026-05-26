from quant_ecosystem.execution.orchestrators.paper_execution_orchestrator import (
    PaperExecutionOrchestrator,
)


class DummyPaperBroker:
    account_source = "PAPER"

    def place_order(
        self,
        symbol,
        side,
        qty,
        price,
    ):
        return {
            "id": "PAPER-001",
            "status": "FILLED",
        }


def test_paper_execution_success():
    orch = PaperExecutionOrchestrator()

    result = orch.execute(
        paper_broker=DummyPaperBroker(),
        normalized_symbol="INFY",
        side="BUY",
        qty=2,
        price=1500,
    )

    assert result["order_id"] == "PAPER-001"
    assert result["broker"] == "PAPER"
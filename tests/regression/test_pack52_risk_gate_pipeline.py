from quant_ecosystem.execution.pipeline.risk_gate_pipeline import (
    GateResult,
    RiskGatePipeline,
)


class ApproveGate:
    def __call__(
        self,
        state,
        signal,
        context,
    ):
        return GateResult(
            allowed=True,
            reason="OK",
            gate="approve",
        )


class RejectGate:
    def __call__(
        self,
        state,
        signal,
        context,
    ):
        return GateResult(
            allowed=False,
            reason="blocked",
            gate="reject",
        )


def test_pipeline_approve():
    pipe = RiskGatePipeline(
        [ApproveGate()]
    )

    result = pipe.check(
        state={},
        signal={"symbol": "TEST"},
        context={},
    )

    assert result.allowed is True


def test_pipeline_reject():
    pipe = RiskGatePipeline(
        [RejectGate()]
    )

    result = pipe.check(
        state={},
        signal={"symbol": "TEST"},
        context={},
    )

    assert result.allowed is False
    assert result.reason == "blocked"
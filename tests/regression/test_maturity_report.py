from quant_ecosystem.cognition.swarm import (
    MaturityLevel,
    MaturityReport,
)


def test_maturity_report():

    report = MaturityReport(
        assessed_domains=5,
        maturity_level=(
            MaturityLevel.OPERATIONAL
        ),
    )

    assert (
        report.maturity_level
        == MaturityLevel.OPERATIONAL
    )
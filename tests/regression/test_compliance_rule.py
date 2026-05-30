from quant_ecosystem.cognition.swarm import (
    ComplianceRule,
)


def test_compliance_rule():

    rule = ComplianceRule(
        rule_id="R1",
        category="governance",
    )

    assert rule.rule_id == "R1"
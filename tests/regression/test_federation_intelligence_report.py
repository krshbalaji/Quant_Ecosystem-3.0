from quant_ecosystem.cognition.swarm import (
    FederationIntelligenceReport,
    KnowledgePattern,
)


def test_report_creation():

    report = FederationIntelligenceReport(
        pattern_count=1,
        patterns=[
            KnowledgePattern(
                category="risk",
                frequency=5,
            )
        ],
    )

    assert report.pattern_count == 1
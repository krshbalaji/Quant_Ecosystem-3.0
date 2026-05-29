from quant_ecosystem.cognition.swarm import (
    ArchitectureForecastReport,
)


def test_forecast_report():

    report = (
        ArchitectureForecastReport(
            projected_growth=20,
            projected_total=120,
        )
    )

    assert report.projected_total == 120
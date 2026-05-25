from quant_ecosystem.monitoring.anomaly_detection_engine import (
    anomaly_detection_engine,
)


def test_slippage_detection():
    result = (
        anomaly_detection_engine
        .slippage_anomaly(
            expected_price=100,
            actual_price=101,
        )
    )

    assert result["anomaly"] is True


def test_fill_detection():
    result = (
        anomaly_detection_engine
        .fill_size_anomaly(
            expected_qty=100,
            actual_qty=60,
        )
    )

    assert result["anomaly"] is True


def test_exposure_detection():
    result = (
        anomaly_detection_engine
        .exposure_anomaly(
            expected_exposure=100000,
            actual_exposure=140000,
        )
    )

    assert result["anomaly"] is True


def test_evaluate():
    result = (
        anomaly_detection_engine
        .evaluate(
            expected_price=100,
            actual_price=101,
            expected_qty=100,
            actual_qty=60,
            expected_exposure=100000,
            actual_exposure=140000,
        )
    )

    assert result["severity"] == "CRITICAL"
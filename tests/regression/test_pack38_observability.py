from quant_ecosystem.observability import (
    metrics_registry,
    runtime_health_engine,
    telemetry_collector,
)


def setup_function():
    metrics_registry.clear()


def test_increment():
    metrics_registry.increment("orders")
    assert metrics_registry.get("orders") == 1


def test_set_metric():
    metrics_registry.set("cpu", 55)
    assert metrics_registry.get("cpu") == 55


def test_health_normal():
    result = runtime_health_engine.classify(
        20,
        30,
        1,
    )
    assert result == "NORMAL"


def test_health_critical():
    result = runtime_health_engine.classify(
        95,
        20,
        1,
    )
    assert result == "CRITICAL"


def test_record_event():
    telemetry_collector.record_event("fills")
    assert metrics_registry.get("fills") == 1


def test_snapshot():
    telemetry_collector.record_event("orders")

    snap = telemetry_collector.runtime_snapshot(
        55,
        60,
        2,
    )

    assert snap["health"] == "WATCH"
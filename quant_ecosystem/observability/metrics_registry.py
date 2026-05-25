class MetricsRegistry:

    def __init__(self):
        self._metrics = {}

    def increment(
        self,
        metric,
        value=1,
    ):
        self._metrics[metric] = (
            self._metrics.get(metric, 0)
            + value
        )

    def set(
        self,
        metric,
        value,
    ):
        self._metrics[metric] = value

    def get(
        self,
        metric,
    ):
        return self._metrics.get(metric)

    def snapshot(self):
        return dict(self._metrics)

    def clear(self):
        self._metrics.clear()


metrics_registry = MetricsRegistry()
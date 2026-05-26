class BrokerHealthRouter:

    def __init__(self):
        self._broker_health = {}

    def mark_healthy(
        self,
        broker_name,
    ):
        self._broker_health[
            broker_name
        ] = True

    def mark_unhealthy(
        self,
        broker_name,
    ):
        self._broker_health[
            broker_name
        ] = False

    def is_healthy(
        self,
        broker_name,
    ):
        return self._broker_health.get(
            broker_name,
            True,
        )

    def select_healthy(
        self,
        broker_registry,
        preferred=None,
    ):
        brokers = broker_registry.all()

        if preferred:
            if (
                preferred in brokers
                and self.is_healthy(preferred)
            ):
                return preferred, brokers[preferred]

        for name, broker in brokers.items():
            if self.is_healthy(name):
                return name, broker

        raise RuntimeError(
            "No healthy brokers available"
        )
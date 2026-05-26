class BrokerFailover:

    def failover(
        self,
        broker_registry,
        failed_name,
    ):
        brokers = broker_registry.all()

        for name, broker in brokers.items():
            if name != failed_name:
                return name, broker

        raise RuntimeError(
            "No failover broker available"
        )
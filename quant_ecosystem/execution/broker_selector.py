class BrokerSelector:

    def select(
        self,
        broker_registry,
        preferred=None,
    ):
        brokers = broker_registry.all()

        if preferred:
            broker = brokers.get(preferred)

            if broker:
                return preferred, broker

        if not brokers:
            raise RuntimeError(
                "No brokers registered"
            )

        name = next(iter(brokers))
        return name, brokers[name]
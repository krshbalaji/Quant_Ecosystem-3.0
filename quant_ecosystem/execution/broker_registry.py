class BrokerRegistry:

    def __init__(self):
        self._brokers = {}

    def register(
        self,
        name,
        broker,
    ):
        self._brokers[name] = broker

    def get(
        self,
        name,
    ):
        return self._brokers.get(name)

    def all(self):
        return dict(self._brokers)
class BrokerResilience:

    def __init__(self):
        self._scores = {}

    def _state(self, broker_name):
        broker_name = str(
            broker_name
        ).lower().strip()

        if broker_name not in self._scores:
            self._scores[broker_name] = {
                "score": 0,
            }

        return self._scores[broker_name]

    def mark_timeout(
        self,
        broker_name,
    ):
        self._state(
            broker_name
        )["score"] += 3

    def mark_disconnect(
        self,
        broker_name,
    ):
        self._state(
            broker_name
        )["score"] += 2

    def mark_failure(
        self,
        broker_name,
    ):
        self._state(
            broker_name
        )["score"] += 1

    def mark_healthy(
        self,
        broker_name,
    ):
        state = self._state(
            broker_name
        )

        if state["score"] > 0:
            state["score"] -= 1

    def is_degraded(
        self,
        broker_name,
    ):
        return (
            self._state(
                broker_name
            )["score"] >= 3
        )

    def score(
        self,
        broker_name,
    ):
        return self._state(
            broker_name
        )["score"]
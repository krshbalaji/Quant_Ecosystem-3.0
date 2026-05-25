class SubscriberRegistry:

    def __init__(self):
        self._subs = {}

    def subscribe(
        self,
        event_name,
        handler,
    ):
        self._subs.setdefault(
            event_name,
            []
        ).append(handler)

    def handlers(
        self,
        event_name,
    ):
        return self._subs.get(
            event_name,
            []
        )

    def clear(self):
        self._subs.clear()


subscriber_registry = (
    SubscriberRegistry()
)
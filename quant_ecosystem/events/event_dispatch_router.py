from quant_ecosystem.events.subscriber_registry import (
    subscriber_registry,
)


class EventDispatchRouter:

    def dispatch(
        self,
        event,
    ):
        results = []

        handlers = (
            subscriber_registry.handlers(
                event.name
            )
        )

        for handler in handlers:
            results.append(
                handler(event)
            )

        return results


event_dispatch_router = (
    EventDispatchRouter()
)
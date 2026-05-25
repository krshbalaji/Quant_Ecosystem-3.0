from quant_ecosystem.events.event_dispatch_router import (
    event_dispatch_router,
)


class EventBus:

    def publish(
        self,
        event,
    ):
        return event_dispatch_router.dispatch(
            event
        )


event_bus = EventBus()
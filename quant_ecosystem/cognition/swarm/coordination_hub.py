from .federation_event import (
    FederationEvent,
)
from .federation_event_bus import (
    FederationEventBus,
)


class CoordinationHub:

    def __init__(
        self,
        bus: FederationEventBus,
    ):
        self.bus = bus

    def coordinate(
        self,
        event: FederationEvent,
    ):

        return self.bus.publish(
            event
        )
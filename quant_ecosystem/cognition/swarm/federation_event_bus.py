from typing import List

from .event_subscription import (
    EventSubscription,
)
from .federation_event import (
    FederationEvent,
)
from .event_dispatch_record import (
    EventDispatchRecord,
)


class FederationEventBus:

    def __init__(self):
        self.subscriptions: List[
            EventSubscription
        ] = []

    def subscribe(
        self,
        subscription: EventSubscription,
    ) -> None:

        self.subscriptions.append(
            subscription
        )

    def publish(
        self,
        event: FederationEvent,
    ) -> List[EventDispatchRecord]:

        records = []

        for subscription in self.subscriptions:

            if (
                subscription.event_type
                == event.event_type
            ):

                records.append(
                    EventDispatchRecord(
                        event_id=event.event_id,
                        subscriber_id=(
                            subscription.subscriber_id
                        ),
                        dispatched=True,
                    )
                )

        return records
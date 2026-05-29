from dataclasses import dataclass


@dataclass(frozen=True)
class EventSubscription:
    subscriber_id: str
    event_type: str
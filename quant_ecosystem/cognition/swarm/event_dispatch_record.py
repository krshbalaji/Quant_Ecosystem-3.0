from dataclasses import dataclass


@dataclass(frozen=True)
class EventDispatchRecord:
    event_id: str
    subscriber_id: str
    dispatched: bool
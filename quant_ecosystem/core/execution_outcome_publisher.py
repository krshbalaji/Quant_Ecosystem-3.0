from typing import Any


class ExecutionOutcomePublisher:
    """Minimal publisher that emits outcomes to an EventBus under topic 'execution.outcome'."""

    def __init__(self, event_bus) -> None:
        self._bus = event_bus

    def publish_outcome(self, outcome: Any) -> None:
        # publish raw outcome to the canonical topic
        self._bus.publish("execution.outcome", outcome)


__all__ = ["ExecutionOutcomePublisher"]

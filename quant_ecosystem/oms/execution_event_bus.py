"""
QE3 OMS execution event bus
Pack22
"""

from collections import defaultdict


class ExecutionEventBus:
    def __init__(self):
        self._subscribers = defaultdict(list)

    def subscribe(self, event_type, callback):
        self._subscribers[event_type].append(callback)

    def publish(self, event):
        callbacks = self._subscribers.get(event.event_type, [])
        for cb in callbacks:
            try:
                cb(event)
            except Exception:
                pass

    def clear(self):
        self._subscribers.clear()


execution_event_bus = ExecutionEventBus()
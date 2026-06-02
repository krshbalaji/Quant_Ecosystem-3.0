from typing import Any, Callable, Dict, List


class EventBus:
    """Minimal in-process EventBusFoundation V1.

    Implements a topic -> ordered-list-of-callables registry using
    Dict[str, List[Callable]]. Subscription order is preserved.
    """

    def __init__(self) -> None:
        self._subs: Dict[str, List[Callable[[Any], None]]] = {}

    def subscribe(self, topic: str, callback: Callable) -> None:
        """Register `callback` for `topic`.

        Duplicate registrations are allowed (callback may be added multiple times).
        """
        if topic not in self._subs:
            self._subs[topic] = []
        self._subs[topic].append(callback)

    def unsubscribe(self, topic: str, callback: Callable) -> None:
        """Remove `callback` from `topic` if present.

        No error is raised if `topic` or `callback` is absent.
        """
        if topic not in self._subs:
            return
        try:
            self._subs[topic].remove(callback)
        except ValueError:
            # callback not present — silent no-op per spec
            pass

    def publish(self, topic: str, event: Any) -> None:
        """Publish `event` to all subscribers of `topic`.

        If no subscribers exist the call is a no-op.
        Subscribers are invoked in registration order.
        Exceptions raised by subscribers propagate to the caller.
        """
        subscribers = self._subs.get(topic)
        if not subscribers:
            return
        # Iterate over a shallow copy to allow subscribers to unsubscribe
        # themselves while iterating without affecting delivery to others.
        for cb in list(subscribers):
            cb(event)


__all__ = ["EventBus"]

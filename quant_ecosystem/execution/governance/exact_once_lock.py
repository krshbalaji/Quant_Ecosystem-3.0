import socket
import uuid

from quant_ecosystem.execution.sovereignty.state_store import (
    sovereign_state_store,
)


class ExactOnceLock:

    def __init__(self):
        self._owner = (
            f"{socket.gethostname()}-"
            f"{uuid.uuid4()}"
        )

    def acquire(
        self,
        key,
        ttl_seconds=30,
    ):
        return sovereign_state_store.acquire_lock(
            lock_key=key,
            owner=self._owner,
            ttl_seconds=ttl_seconds,
        )

    def release(
        self,
        key,
    ):
        sovereign_state_store.release_lock(
            lock_key=key,
            owner=self._owner,
        )
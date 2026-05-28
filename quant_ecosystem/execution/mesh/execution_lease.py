import time


class ExecutionLease:

    def __init__(self):

        self._leases = {}

    def acquire(
        self,
        lease_key,
        node_id,
        ttl=30,
    ):

        now = time.time()

        current = self._leases.get(
            lease_key
        )

        if current:

            if current["expires"] > now:
                return False

        self._leases[
            lease_key
        ] = {
            "node_id": node_id,
            "expires": now + ttl,
        }

        return True

    def release(
        self,
        lease_key,
        node_id,
    ):

        current = self._leases.get(
            lease_key
        )

        if not current:
            return

        if (
            current["node_id"]
            != node_id
        ):
            return

        self._leases.pop(
            lease_key,
            None,
        )


execution_lease = (
    ExecutionLease()
)
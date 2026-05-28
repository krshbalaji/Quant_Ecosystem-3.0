import time


class NodeRegistry:

    def __init__(self):

        self._nodes = {}

    def heartbeat(
        self,
        node_id,
    ):

        self._nodes[node_id] = {
            "last_seen": time.time(),
        }

    def active_nodes(
        self,
        timeout=30,
    ):

        now = time.time()

        active = []

        for node_id, meta in (
            self._nodes.items()
        ):

            age = (
                now
                - meta["last_seen"]
            )

            if age <= timeout:
                active.append(node_id)

        return active


node_registry = NodeRegistry()
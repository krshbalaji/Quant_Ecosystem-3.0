import socket
import uuid


class NodeIdentity:

    def __init__(self):

        self._node_id = (
            f"{socket.gethostname()}-"
            f"{uuid.uuid4().hex[:8]}"
        )

    @property
    def node_id(self):
        return self._node_id


node_identity = NodeIdentity()
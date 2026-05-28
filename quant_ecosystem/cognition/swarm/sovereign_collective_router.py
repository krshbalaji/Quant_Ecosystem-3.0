from typing import List

from .swarm_message import SwarmMessage
from .trust_registry import TrustRegistry


class SovereignCollectiveRouter:

    def __init__(self, trust_registry: TrustRegistry):
        self.trust_registry = trust_registry
        self.message_log: List[SwarmMessage] = []

    def route(
        self,
        message: SwarmMessage,
        required_capability: str,
    ) -> bool:

        trusted = self.trust_registry.evaluate_trust(
            message.sender_id,
            required_capability,
        )

        if not trusted:
            return False

        self.message_log.append(message)

        return True
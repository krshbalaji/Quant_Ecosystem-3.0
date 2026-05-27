class BrokerRegistry:
    """
    Institutional broker identity registry.
    Backward compatible with legacy broker lookup.
    """

    def __init__(self):
        self._brokers = {}
        self._identities = {}

    def register(
        self,
        name,
        broker,
        account_id=None,
        priority=100,
        enabled=True,
        risk_profile="STANDARD",
    ):
        key = str(name).lower().strip()

        self._brokers[key] = broker

        family = getattr(
            broker,
            "broker_name",
            key,
        ).lower().strip()

        identity = {
            "name": key,
            "broker": broker,
            "account_id": (
                account_id
                or key
            ),
            "priority": priority,
            "enabled": enabled,
            "risk_profile": risk_profile,
            "family": family,
        }

        self._identities.setdefault(
            family,
            []
        ).append(identity)

        self._identities[family].sort(
            key=lambda x: x["priority"]
        )

    def get(
        self,
        name,
    ):
        return self._brokers.get(
            str(name).lower().strip()
        )

    def all(self):
        return dict(self._brokers)

    def get_candidates(
        self,
        broker_family,
    ):
        family = str(
            broker_family
        ).lower().strip()

        return list(
            self._identities.get(
                family,
                []
            )
        )

    def select_identity(
        self,
        broker_family,
        selector_fn=None,
    ):
        candidates = self.get_candidates(
            broker_family
        )

        enabled = [
            c for c in candidates
            if c["enabled"]
        ]

        if not enabled:
            return None

        if selector_fn:
            return selector_fn(
                enabled
            )

        return enabled[0]
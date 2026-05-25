class AuditRepository:

    def __init__(self):
        self._audit = []

    def record(
        self,
        event_name,
        payload,
    ):
        self._audit.append(
            {
                "event_name": event_name,
                "payload": payload,
            }
        )

    def all_records(self):
        return list(self._audit)

    def by_event(
        self,
        event_name,
    ):
        return [
            x for x in self._audit
            if x["event_name"] == event_name
        ]

    def clear(self):
        self._audit.clear()


audit_repo = (
    AuditRepository()
)
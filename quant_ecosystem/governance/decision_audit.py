from copy import deepcopy


class DecisionAudit:

    def __init__(self):
        self._events = []

    def record(
        self,
        decision_type,
        decision_payload,
        rationale="",
    ):
        payload = {
            "decision_type": decision_type,
            "decision_payload": deepcopy(
                decision_payload
            ),
            "rationale": rationale,
        }

        self._events.append(payload)

        return payload

    def history(self):
        return deepcopy(
            self._events
        )

    def clear(self):
        self._events.clear()


decision_audit = DecisionAudit()
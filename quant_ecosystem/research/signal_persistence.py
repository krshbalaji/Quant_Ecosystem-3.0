from copy import deepcopy


class SignalPersistenceLayer:

    def __init__(self):
        self._signal_journal = []
        self._hypothesis_archive = []
        self._audit_trail = []

    def record_signal(
        self,
        signal,
    ):
        payload = deepcopy(signal)

        self._signal_journal.append(
            payload
        )

        self._audit_trail.append(
            {
                "event": "SIGNAL_RECORDED",
                "payload": payload,
            }
        )

        return payload

    def archive_hypothesis(
        self,
        hypothesis,
    ):
        payload = deepcopy(hypothesis)

        self._hypothesis_archive.append(
            payload
        )

        self._audit_trail.append(
            {
                "event": "HYPOTHESIS_ARCHIVED",
                "payload": payload,
            }
        )

        return payload

    def signal_journal(self):
        return deepcopy(
            self._signal_journal
        )

    def hypothesis_archive(self):
        return deepcopy(
            self._hypothesis_archive
        )

    def audit_trail(self):
        return deepcopy(
            self._audit_trail
        )

    def replay_ledger(self):
        return deepcopy(
            self._signal_journal
        )

    def clear(self):
        self._signal_journal.clear()
        self._hypothesis_archive.clear()
        self._audit_trail.clear()


signal_persistence_layer = (
    SignalPersistenceLayer()
)
class TransactionCoordinator:

    def __init__(self):
        self._active = False

    def begin(self):
        self._active = True

    def commit(self):
        self._active = False

    def rollback(self):
        self._active = False

    def active(self):
        return self._active


transaction_coordinator = (
    TransactionCoordinator()
)
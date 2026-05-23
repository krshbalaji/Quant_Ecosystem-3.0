class BrokerAuthError(RuntimeError):
    pass


class BrokerRejectError(RuntimeError):
    pass


class BrokerTimeoutError(RuntimeError):
    pass


class BrokerProtocolError(RuntimeError):
    pass


class ExecutionIntegrityError(RuntimeError):
    pass
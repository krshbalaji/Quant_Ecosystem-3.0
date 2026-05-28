class ProtectionState:

    def __init__(self):

        self._throttled = False

        self._degraded = False

        self._emergency = False

    def enable_throttle(self):

        self._throttled = True

    def disable_throttle(self):

        self._throttled = False

    def throttled(self):

        return self._throttled

    def enable_degraded(self):

        self._degraded = True

    def disable_degraded(self):

        self._degraded = False

    def degraded(self):

        return self._degraded

    def enable_emergency(self):

        self._emergency = True

    def disable_emergency(self):

        self._emergency = False

    def emergency(self):

        return self._emergency


protection_state = (
    ProtectionState()
)
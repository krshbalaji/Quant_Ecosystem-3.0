class LifecycleManager:

    def __init__(self):
        self._state = "STOPPED"

    def start(self):
        self._state = "RUNNING"

    def stop(self):
        self._state = "STOPPED"

    def restart(self):
        self.stop()
        self.start()

    def state(self):
        return self._state


lifecycle_manager = (
    LifecycleManager()
)
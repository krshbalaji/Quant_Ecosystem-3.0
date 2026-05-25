class StateManager:

    def __init__(self):
        self._state = {}

    def set(
        self,
        key,
        value,
    ):
        self._state[key] = value

    def get(
        self,
        key,
    ):
        return self._state.get(key)

    def snapshot(self):
        return dict(self._state)

    def restore(
        self,
        snapshot,
    ):
        self._state = dict(snapshot)

    def clear(self):
        self._state.clear()


state_manager = StateManager()
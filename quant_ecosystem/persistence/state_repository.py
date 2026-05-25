from quant_ecosystem.persistence.repository_contracts import (
    RepositoryContract,
)


class StateRepository(
    RepositoryContract
):

    def __init__(self):
        self._state = {}

    def save(
        self,
        key,
        value,
    ):
        self._state[key] = value

    def load(
        self,
        key,
    ):
        return self._state.get(key)

    def delete(
        self,
        key,
    ):
        if key in self._state:
            del self._state[key]

    def snapshot(self):
        return dict(self._state)

    def clear(self):
        self._state.clear()


state_repository = (
    StateRepository()
)
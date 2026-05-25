from quant_ecosystem.state.state_manager import (
    state_manager,
)


class StateTransitionController:

    def transition(
        self,
        key,
        value,
    ):
        previous = state_manager.get(key)

        state_manager.set(
            key,
            value,
        )

        return {
            "previous": previous,
            "current": value,
        }


state_transition_controller = (
    StateTransitionController()
)
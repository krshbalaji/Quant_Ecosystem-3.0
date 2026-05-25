from quant_ecosystem.security import (
    access_controller,
)


class GovernanceEndpoint:

    def authorize(
        self,
        token,
        role,
        action,
    ):
        return access_controller.authorize(
            token,
            role,
            action,
        )


governance_endpoint = (
    GovernanceEndpoint()
)
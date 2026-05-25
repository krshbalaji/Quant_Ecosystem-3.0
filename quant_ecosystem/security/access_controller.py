from quant_ecosystem.security.token_validator import (
    token_validator,
)

from quant_ecosystem.security.permission_engine import (
    permission_engine,
)


class AccessController:

    def authorize(
        self,
        token,
        role,
        action,
    ):
        if not token_validator.validate(
            token
        ):
            return False

        return permission_engine.allowed(
            role,
            action,
        )


access_controller = AccessController()
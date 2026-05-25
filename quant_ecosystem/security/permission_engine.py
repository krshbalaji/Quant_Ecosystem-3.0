class PermissionEngine:

    def allowed(
        self,
        role,
        action,
    ):
        matrix = {
            "admin": {"trade", "config", "risk"},
            "viewer": {"view"},
        }

        return action in matrix.get(
            role,
            set(),
        )


permission_engine = PermissionEngine()
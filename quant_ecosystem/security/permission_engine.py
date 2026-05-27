class PermissionEngine:

    MATRIX = {
        "admin": {
            "trade",
            "config",
            "risk",
            "audit",
            "kill",
            "override",
            "view",
        },
        "trader": {
            "trade",
            "view",
        },
        "risk_officer": {
            "risk",
            "kill",
            "view",
            "audit",
        },
        "auditor": {
            "audit",
            "view",
        },
        "viewer": {
            "view",
        },
        "emergency": {
            "kill",
            "override",
            "view",
        },
    }

    def allowed(
        self,
        role,
        action,
    ):
        role = str(role).lower().strip()
        action = str(action).lower().strip()

        return action in self.MATRIX.get(
            role,
            set(),
        )


permission_engine = PermissionEngine()
class BackendGovernance:

    VALID = {
        "sqlite",
        "file",
    }

    def allowed(
        self,
        backend,
    ):
        return backend in self.VALID


backend_governance = (
    BackendGovernance()
)
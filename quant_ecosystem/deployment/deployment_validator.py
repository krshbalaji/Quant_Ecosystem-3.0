class DeploymentValidator:

    VALID_ENVIRONMENTS = {
        "dev",
        "staging",
        "prod",
    }

    def validate(
        self,
        config,
    ):
        return (
            config.environment
            in self.VALID_ENVIRONMENTS
        )


deployment_validator = (
    DeploymentValidator()
)
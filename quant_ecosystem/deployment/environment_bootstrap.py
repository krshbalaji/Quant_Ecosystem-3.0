class EnvironmentBootstrap:

    def bootstrap(
        self,
        config,
    ):
        return {
            "environment": config.environment,
            "runtime_mode": config.runtime_mode,
            "bootstrapped": True,
        }


environment_bootstrap = (
    EnvironmentBootstrap()
)
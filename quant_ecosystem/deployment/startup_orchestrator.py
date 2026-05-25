from quant_ecosystem.runtime import (
    lifecycle_manager,
)

from quant_ecosystem.deployment.environment_bootstrap import (
    environment_bootstrap,
)

from quant_ecosystem.deployment.deployment_validator import (
    deployment_validator,
)


class StartupOrchestrator:

    def launch(
        self,
        config,
    ):
        if not deployment_validator.validate(
            config
        ):
            raise ValueError(
                "Invalid deployment config"
            )

        environment_bootstrap.bootstrap(
            config
        )

        lifecycle_manager.start()

        return lifecycle_manager.state()


startup_orchestrator = (
    StartupOrchestrator()
)
from quant_ecosystem.configuration.config_models import (
    RuntimeConfig,
)


class EnvironmentProfiles:

    def dev(self):
        return RuntimeConfig(
            environment="DEV",
            broker="SIM",
            mode="PAPER",
        )

    def staging(self):
        return RuntimeConfig(
            environment="STAGING",
            broker="SIM",
            mode="PAPER",
        )

    def prod(self):
        return RuntimeConfig(
            environment="PROD",
            broker="LIVE",
            mode="LIVE",
        )


environment_profiles = (
    EnvironmentProfiles()
)
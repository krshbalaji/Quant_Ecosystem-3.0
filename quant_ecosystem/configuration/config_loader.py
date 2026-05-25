from quant_ecosystem.configuration.environment_profiles import (
    environment_profiles,
)


class ConfigLoader:

    def load(
        self,
        environment,
    ):
        env = environment.upper()

        mapping = {
            "DEV": environment_profiles.dev,
            "STAGING": environment_profiles.staging,
            "PROD": environment_profiles.prod,
        }

        if env not in mapping:
            raise ValueError(
                f"Unknown environment: {environment}"
            )

        return mapping[env]()


config_loader = ConfigLoader()
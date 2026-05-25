class ConfigValidator:

    VALID_ENV = {
        "DEV",
        "STAGING",
        "PROD",
    }

    VALID_MODE = {
        "PAPER",
        "LIVE",
    }

    def validate(
        self,
        config,
    ):
        errors = []

        if config.environment not in self.VALID_ENV:
            errors.append(
                "INVALID_ENVIRONMENT"
            )

        if config.mode not in self.VALID_MODE:
            errors.append(
                "INVALID_MODE"
            )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }


config_validator = (
    ConfigValidator()
)
from quant_ecosystem.runtime.dependency_registry import (
    dependency_registry,
)


class StartupValidator:

    REQUIRED = [
        "market_data",
        "execution",
        "risk",
    ]

    def validate(self):
        missing = []

        for dep in self.REQUIRED:
            if not dependency_registry.exists(dep):
                missing.append(dep)

        return {
            "valid": len(missing) == 0,
            "missing": missing,
        }


startup_validator = (
    StartupValidator()
)
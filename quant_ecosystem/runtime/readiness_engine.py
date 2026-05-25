from quant_ecosystem.runtime.startup_validator import (
    startup_validator,
)


class ReadinessEngine:

    def ready(self):
        result = startup_validator.validate()
        return result["valid"]


readiness_engine = ReadinessEngine()
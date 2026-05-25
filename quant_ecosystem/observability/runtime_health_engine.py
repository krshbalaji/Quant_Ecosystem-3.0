class RuntimeHealthEngine:

    def classify(
        self,
        cpu_pct,
        memory_pct,
        error_rate,
    ):
        if (
            cpu_pct >= 90
            or memory_pct >= 90
            or error_rate >= 20
        ):
            return "CRITICAL"

        if (
            cpu_pct >= 75
            or memory_pct >= 75
            or error_rate >= 10
        ):
            return "HIGH"

        if (
            cpu_pct >= 50
            or memory_pct >= 50
            or error_rate >= 5
        ):
            return "WATCH"

        return "NORMAL"


runtime_health_engine = (
    RuntimeHealthEngine()
)
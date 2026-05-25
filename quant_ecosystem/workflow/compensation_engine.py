class CompensationEngine:

    def compensate(
        self,
        handlers,
    ):
        results = []

        for handler in handlers:
            results.append(
                handler()
            )

        return results


compensation_engine = (
    CompensationEngine()
)
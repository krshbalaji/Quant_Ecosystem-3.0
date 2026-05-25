class BrokerMemory:

    def __init__(self):
        self._memory = {}

    def record_execution(
        self,
        broker,
        slippage_bps,
        success=True,
    ):
        if broker not in self._memory:
            self._memory[broker] = []

        self._memory[broker].append(
            {
                "slippage_bps": slippage_bps,
                "success": success,
            }
        )

    def average_slippage(
        self,
        broker,
    ):
        rows = self._memory.get(
            broker,
            []
        )

        if not rows:
            return 0

        return sum(
            x["slippage_bps"]
            for x in rows
        ) / len(rows)

    def success_rate(
        self,
        broker,
    ):
        rows = self._memory.get(
            broker,
            []
        )

        if not rows:
            return 0

        success = len(
            [
                x for x in rows
                if x["success"]
            ]
        )

        return success / len(rows)

    def broker_snapshot(
        self,
        broker,
    ):
        return {
            "avg_slippage": (
                self.average_slippage(
                    broker
                )
            ),
            "success_rate": (
                self.success_rate(
                    broker
                )
            ),
        }

    def clear(self):
        self._memory.clear()


broker_memory = BrokerMemory()
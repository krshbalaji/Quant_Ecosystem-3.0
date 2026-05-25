class StrategyExecutionContext:

    def __init__(self):
        self._ownership = {}

    def attach(
        self,
        order_id,
        strategy_id,
        metadata=None,
    ):
        self._ownership[order_id] = {
            "strategy_id": strategy_id,
            "metadata": metadata or {},
        }

    def get(
        self,
        order_id,
    ):
        return self._ownership.get(order_id)

    def strategy_for_order(
        self,
        order_id,
    ):
        ctx = self.get(order_id)

        if not ctx:
            return None

        return ctx.get("strategy_id")

    def remove(
        self,
        order_id,
    ):
        self._ownership.pop(order_id, None)

    def clear(self):
        self._ownership.clear()

    def all_orders(self):
        return dict(self._ownership)


strategy_execution_context = StrategyExecutionContext()
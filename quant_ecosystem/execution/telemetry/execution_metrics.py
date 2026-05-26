class ExecutionMetrics:

    def __init__(self):
        self.orders_attempted = 0
        self.orders_completed = 0
        self.orders_failed = 0

    def record_attempt(self):
        self.orders_attempted += 1

    def record_success(self):
        self.orders_completed += 1

    def record_failure(self):
        self.orders_failed += 1

    def snapshot(self):
        return {
            "orders_attempted": self.orders_attempted,
            "orders_completed": self.orders_completed,
            "orders_failed": self.orders_failed,
        }
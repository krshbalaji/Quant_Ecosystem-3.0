class ExecutionMetrics:

    def __init__(self):
        self.orders_attempted = 0
        self.orders_completed = 0
        self.orders_failed = 0

        self.orders_uncertain = 0
        self.orders_recovered = 0
        self.orders_deadletter = 0

        self.cancel_requests = 0
        self.modify_requests = 0

        self.sla_breaches = 0

        self.watchdog_incidents = 0
        self.quarantine_incidents = 0

    def record_attempt(self):
        self.orders_attempted += 1

    def record_success(self):
        self.orders_completed += 1

    def record_failure(self):
        self.orders_failed += 1

    def record_uncertain(self):
        self.orders_uncertain += 1

    def record_recovered(self):
        self.orders_recovered += 1

    def record_deadletter(self):
        self.orders_deadletter += 1

    def record_cancel(self):
        self.cancel_requests += 1

    def record_modify(self):
        self.modify_requests += 1

    def record_sla_breach(self):
        self.sla_breaches += 1

    def record_watchdog_incident(self):
        self.watchdog_incidents += 1

    def record_quarantine_incident(self):
        self.quarantine_incidents += 1
        
    def snapshot(self):
        return {
            "orders_attempted": self.orders_attempted,
            "orders_completed": self.orders_completed,
            "orders_failed": self.orders_failed,
            "orders_uncertain": self.orders_uncertain,
            "orders_recovered": self.orders_recovered,
            "orders_deadletter": self.orders_deadletter,
            "cancel_requests": self.cancel_requests,
            "modify_requests": self.modify_requests,
            "sla_breaches": self.sla_breaches,
            "watchdog_incidents": self.watchdog_incidents,
            "quarantine_incidents": self.quarantine_incidents,
        }

        
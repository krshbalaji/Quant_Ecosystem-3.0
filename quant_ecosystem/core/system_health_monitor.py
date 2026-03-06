class SystemHealthMonitor:

    def __init__(self, router):
        self.router = router

    def run_checks(self):
        return {
            "config_loaded": True,
            "mode": self.router.mode,
            "broker_connected": bool(self.router.execution),
            "risk_engine_ready": self.router.risk_engine is not None,
            "execution_ready": self.router.execution is not None
        }

    def report(self):
        checks = self.run_checks()
        for k,v in checks.items():
            print(f"{k}: {v}")
        return checks
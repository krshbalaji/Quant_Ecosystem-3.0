from core.config_loader import Config


class HealthCheck:

    def run(self, router=None):
        config = Config()
        checks = {
            "config_loaded": True,
            "mode": config.mode,
            "broker_connected": False,
            "risk_engine_ready": False,
            "execution_ready": False,
        }

        if router:
            try:
                checks["broker_connected"] = bool(router.broker.get_balance())
            except Exception:
                checks["broker_connected"] = False

            checks["risk_engine_ready"] = hasattr(router, "risk_engine")
            checks["execution_ready"] = hasattr(router, "run_cycle")

        print("Running system diagnostics...")
        print(f"Health checks: {checks}")
        return checks

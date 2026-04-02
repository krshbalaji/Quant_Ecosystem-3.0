import logging

from quant_ecosystem.operating.core.config_loader import Config


logger = logging.getLogger(__name__)


class HealthCheck:

    def run(self, router=None):
        config = Config()
        mode = str(getattr(config, "mode", "PAPER")).upper()
        checks = {
            "config_loaded": True,
            "mode": mode,
            "broker_connected": mode == "PAPER",
            "risk_engine_ready": False,
            "execution_ready": False,
        }

        if router:
            router_mode = str(
                getattr(
                    getattr(router, "state", None),
                    "trading_mode",
                    getattr(getattr(router, "config", None), "mode", mode),
                )
            ).upper()
            checks["mode"] = router_mode
            checks["broker_connected"] = router_mode == "PAPER"
            broker = (
                getattr(getattr(router, "execution_router", None), "broker", None)
                or getattr(router, "_broker_router", None)
                or getattr(router, "_broker", None)
            )
            try:
                if router_mode == "PAPER":
                    logger.info("PAPER MODE -> skipping broker connectivity requirement")
                    checks["broker_connected"] = True
                elif broker is not None and hasattr(broker, "is_connected"):
                    checks["broker_connected"] = bool(broker.is_connected())
                elif broker is not None and hasattr(broker, "get_balance"):
                    checks["broker_connected"] = bool(broker.get_balance())
                else:
                    checks["broker_connected"] = False
            except Exception:
                checks["broker_connected"] = False

            checks["risk_engine_ready"] = hasattr(router, "risk_engine")
            checks["execution_ready"] = (
                getattr(router, "execution_router", None) is not None
                or hasattr(router, "execute")
            )

        logger.info("Running system diagnostics...")
        logger.info("Health checks: %s", checks)
        return checks

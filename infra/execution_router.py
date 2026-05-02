from config import Config
from infra.logger import get_logger
from infra.cloud_executor import execute_cloud_trade
from infra.health import is_cloud_alive

logger = get_logger(__name__)


def route_execution(data):
    if not any(key in data for key in ("price", "stop_loss", "take_profit")):
        logger.info("Routing signal payload through cloud executor")
        return execute_cloud_trade(data)

    mode = Config.EXECUTION_MODE
    logger.info("Routing execution payload (mode=%s)", mode)

    if mode == "local":
        return {"success": True, "mode": "local", "data": data, "reason": "forced_local"}

    if mode == "cloud":
        return execute_cloud_trade(data)

    if mode == "auto":
        if is_cloud_alive():
            return execute_cloud_trade(data)

        logger.warning("Cloud unavailable, falling back to local execution")
        return {"success": True, "mode": "local", "data": data, "reason": "cloud_unavailable"}

    logger.warning("Unknown execution mode %s, defaulting to auto behavior", mode)
    if is_cloud_alive():
        return execute_cloud_trade(data)
    return {"success": True, "mode": "local", "data": data, "reason": "unknown_mode"}

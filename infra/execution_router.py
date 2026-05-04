from config import Config
from infra.logger import get_logger
from infra.cloud_executor import execute_cloud_trade
from infra.health import is_cloud_alive

logger = get_logger(__name__)

from infra.cloud_executor import execute_cloud_trade


def route_execution(data):
    result = execute_cloud_trade(data)

    if not result:
        print("[FALLBACK] Local execution")

    return result
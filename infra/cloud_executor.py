from infra.http_client import HttpClient
from infra.logger import get_logger

logger = get_logger(__name__)
client = HttpClient()


def execute_cloud_trade(data):
    endpoint = "/trade" if any(key in data for key in ("price", "stop_loss", "take_profit")) else "/signal"
    logger.info("Sending cloud request to %s", endpoint)
    result = client.send_post(endpoint, data)

    if endpoint == "/trade" and result.get("status_code") == 404:
        logger.warning("/trade endpoint not found, falling back to /signal")
        result = client.send_post("/signal", data)

    if not result.get("success"):
        logger.error("Cloud executor failed (%s): %s", endpoint, result.get("error"))
    return result

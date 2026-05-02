from infra.http_client import HttpClient
from infra.logger import get_logger

logger = get_logger(__name__)
client = HttpClient()


def is_cloud_alive() -> bool:
    result = client.send_get("/health", timeout=3)
    if result.get("success"):
        return True

    if result.get("status_code") == 404:
        fallback = client.send_get("/", timeout=3)
        if fallback.get("success"):
            return True

    logger.warning("Cloud health check failed: %s", result.get("error"))
    return False

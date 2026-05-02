import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import Config
from infra.logger import get_logger

logger = get_logger(__name__)


class HttpClient:
    def __init__(self):
        self.session = requests.Session()
        retry_strategy = Retry(
            total=Config.MAX_RETRIES,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
            backoff_factor=0.5,
            raise_on_status=False,
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.headers = {"X-API-KEY": Config.API_KEY}

        if not Config.API_KEY:
            logger.warning("X-API-KEY is not configured; requests may be rejected.")

    def _build_url(self, endpoint: str) -> str:
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            return endpoint
        if not Config.API_BASE_URL:
            raise ValueError("API_BASE_URL is not configured")
        return f"{Config.API_BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"

    def _parse_json(self, response):
        try:
            return response.json()
        except ValueError:
            return None

    def send_get(self, endpoint: str, timeout: int | None = None):
        url = self._build_url(endpoint)
        try:
            response = self.session.get(
                url,
                headers=self.headers,
                timeout=timeout or Config.REQUEST_TIMEOUT,
            )
            data = self._parse_json(response)
            return {
                "success": response.ok,
                "status_code": response.status_code,
                "data": data,
                "error": None if response.ok else response.text,
            }
        except requests.RequestException as exc:
            logger.error("HTTP GET failed: %s", exc)
            return {
                "success": False,
                "status_code": None,
                "data": None,
                "error": str(exc),
            }

    def send_post(self, endpoint: str, payload, timeout: int | None = None):
        url = self._build_url(endpoint)
        try:
            response = self.session.post(
                url,
                json=payload,
                headers=self.headers,
                timeout=timeout or Config.REQUEST_TIMEOUT,
            )
            data = self._parse_json(response)
            return {
                "success": response.ok,
                "status_code": response.status_code,
                "data": data,
                "error": None if response.ok else response.text,
            }
        except requests.RequestException as exc:
            logger.error("HTTP POST failed: %s", exc)
            return {
                "success": False,
                "status_code": None,
                "data": None,
                "error": str(exc),
            }

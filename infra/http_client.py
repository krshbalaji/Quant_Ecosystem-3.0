import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import Config
from infra.logger import get_logger

logger = get_logger(__name__)


class HttpClient:
    def __init__(self):
        self.session = requests.Session()

        retries = Retry(
            total=Config.MAX_RETRIES,
            backoff_factor=Config.BACKOFF_FACTOR,
            status_forcelist=[500, 502, 503, 504],
        )

        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        self.headers = {
            "Content-Type": "application/json",
            "X-API-KEY": Config.API_KEY
        }

    def post(self, url, json):
        return self.session.post(
            url,
            json=json,
            headers=self.headers,
            timeout=Config.TIMEOUT
        )
        
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

    def is_cloud_alive():
        try:
            r = requests.get(Config.CLOUD_BASE_URL, timeout=2)
            return r.status_code == 200
        except:
            return False
            
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

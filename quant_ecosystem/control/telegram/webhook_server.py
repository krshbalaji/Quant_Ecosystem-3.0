import json
import threading
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class TelegramWebhookServer:

    def __init__(self, host, port, path, secret_token=""):
        self.host = host
        self.port = port
        self.path = path
        self.secret_token = secret_token
        self._queue = deque()
        self._lock = threading.Lock()
        self._server = None
        self._thread = None

    def start(self):
        if self._server:
            return

        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                if self.path != owner.path:
                    self.send_response(404)
                    self.end_headers()
                    return

                if owner.secret_token:
                    received = self.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
                    if received != owner.secret_token:
                        self.send_response(403)
                        self.end_headers()
                        return

                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length) if length > 0 else b"{}"
                try:
                    payload = json.loads(body.decode("utf-8"))
                except Exception:
                    payload = {}

                with owner._lock:
                    owner._queue.append(payload)

                self.send_response(200)
                self.end_headers()

            def log_message(self, format, *args):
                return

        self._server = ThreadingHTTPServer((self.host, self.port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self):
        if not self._server:
            return
        self._server.shutdown()
        self._server.server_close()
        self._server = None
        self._thread = None

    def consume(self):
        with self._lock:
            items = list(self._queue)
            self._queue.clear()
            return items

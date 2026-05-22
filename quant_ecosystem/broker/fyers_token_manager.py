import os
import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from fyers_apiv3 import fyersModel
from config.env_loader import Env


class TokenCaptureHandler(BaseHTTPRequestHandler):
    auth_code = None

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if "auth_code" in params:
            TokenCaptureHandler.auth_code = params["auth_code"][0]

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            self.wfile.write(
                b"""
                <html>
                <body>
                <h2>FYERS Authentication Successful</h2>
                <p>You can close this window.</p>
                </body>
                </html>
                """
            )
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, format, *args):
        return


class FyersTokenManager:
    def __init__(self):
        self.client_id = Env.FYERS_CLIENT_ID or Env.FYERS_APP_ID
        self.secret_key = Env.FYERS_SECRET_KEY
        self.redirect_uri = Env.FYERS_REDIRECT_URI

    def _start_callback_server(self):
        parsed = urlparse(self.redirect_uri)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 5000

        server = HTTPServer((host, port), TokenCaptureHandler)

        thread = threading.Thread(target=server.handle_request)
        thread.daemon = True
        thread.start()

        return server

    def _update_env_token(self, token):
        env_path = ".env"

        if not os.path.exists(env_path):
            raise FileNotFoundError(".env file not found")

        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        updated = False
        new_lines = []

        for line in lines:
            if line.startswith("FYERS_ACCESS_TOKEN="):
                new_lines.append(f"FYERS_ACCESS_TOKEN={token}\n")
                updated = True
            else:
                new_lines.append(line)

        if not updated:
            new_lines.append(f"\nFYERS_ACCESS_TOKEN={token}\n")

        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        os.environ["FYERS_ACCESS_TOKEN"] = token

    def generate_token(self):
        session = fyersModel.SessionModel(
            client_id=self.client_id,
            secret_key=self.secret_key,
            redirect_uri=self.redirect_uri,
            response_type="code",
            grant_type="authorization_code",
        )

        auth_url = session.generate_authcode()

        print("Opening FYERS login...")
        print(auth_url)

        self._start_callback_server()
        webbrowser.open(auth_url)

        print("Waiting for FYERS callback...")

        while TokenCaptureHandler.auth_code is None:
            pass

        auth_code = TokenCaptureHandler.auth_code

        session.set_token(auth_code)

        token_response = session.generate_token()

        print("TOKEN RESPONSE =", token_response)

        if token_response.get("s") != "ok":
            raise RuntimeError(
                f"Token generation failed: {json.dumps(token_response)}"
            )

        access_token = (
            token_response.get("access_token")
            or token_response.get("data", {}).get("access_token")
        )

        if not access_token:
            raise RuntimeError("No access token returned from FYERS")

        self._update_env_token(access_token)

        print("FYERS token updated successfully.")

        return access_token

    def validate(self):
        token = os.getenv("FYERS_ACCESS_TOKEN")

        if not token:
            raise RuntimeError("No FYERS_ACCESS_TOKEN found")

        client = fyersModel.FyersModel(
            client_id=self.client_id,
            token=token,
            is_async=False,
            log_path=""
        )

        print("Funds:")
        print(client.funds())

        print("Holdings:")
        print(client.holdings())

        print("Positions:")
        print(client.positions())


def main():
    mgr = FyersTokenManager()
    mgr.generate_token()
    mgr.validate()


if __name__ == "__main__":
    main()
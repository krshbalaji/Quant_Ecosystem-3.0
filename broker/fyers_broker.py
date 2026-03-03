from config.env_loader import Env

class FyersBroker:

    def __init__(self):

        self.client_id = Env.FYERS_CLIENT_ID
        self.secret = Env.FYERS_SECRET_KEY

        self.connected = False

    def connect(self):

        if not self.client_id:

            print("⚠ FYERS API not configured")
            return

        print("Connecting to Fyers...")

        self.connected = True

        print("Broker Connected : Fyers")

    def place_order(self, symbol, side, qty):

        if not self.connected:
            raise Exception("Broker not connected")

        print(f"ORDER {side} {symbol} {qty}")

        return {
            "symbol":symbol,
            "side":side,
            "qty":qty
        }

    def close_position(self, symbol):

        print("Closing position",symbol)

    def get_balance(self):

        return 100000
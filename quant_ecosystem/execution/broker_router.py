import logging

logger = logging.getLogger(__name__)


class BrokerRouter:
    """
    Routes orders to the correct broker.
    Supports multiple brokers (Fyers, Zerodha, Paper broker etc.)
    """

    def __init__(self, broker=None):
        self.broker = broker
        logger.info("BrokerRouter initialized")

    def place_order(self, symbol, side, quantity, order_type="MARKET"):

        if not self.broker:
            raise Exception("No broker connected")

        order = {
            "symbol": symbol,
            "side": side,
            "qty": quantity,
            "type": order_type
        }

        logger.info(f"Routing order → {order}")

        return self.broker.place_order(order)

    def cancel_order(self, order_id):

        if not self.broker:
            raise Exception("No broker connected")

        return self.broker.cancel_order(order_id)

    def positions(self):

        if not self.broker:
            return []

        return self.broker.get_positions()
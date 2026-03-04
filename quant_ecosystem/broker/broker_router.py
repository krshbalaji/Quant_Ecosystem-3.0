class BrokerRouter:

    def __init__(self, broker):

        self.broker = broker

    def place_order(self, symbol, side, qty, **kwargs):

        return self.broker.place_order(symbol, side, qty, **kwargs)

    def close_position(self, symbol):

        return self.broker.close_position(symbol)

    def get_balance(self):

        return self.broker.get_balance()

    def get_orders(self):

        return self.broker.get_orders()

    def get_positions(self):

        return self.broker.get_positions()

    def get_account_snapshot(self, latest_prices=None):

        return self.broker.get_account_snapshot(latest_prices=latest_prices)

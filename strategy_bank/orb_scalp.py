
from pyalgotrading.strategy import StrategyBase

class ORBScalp(StrategyBase):

    name = "ORB Scalper"

    def initialize(self):
        self.orders = {}

    def strategy_select_instruments_for_entry(self , candle , bucket):

        selected , meta = [] , []

        for instrument in bucket:

            hist = self.get_historical_data(instrument)

            if hist is None or len(hist) < 20:
                continue

            high = hist["high"].iloc[-10:].max()
            low = hist["low"].iloc[-10:].min()
            price = hist["close"].iloc[-1]

            if price > high:
                selected.append(instrument)
                meta.append({"action":"BUY"})

            elif price < low:
                selected.append(instrument)
                meta.append({"action":"SELL"})

        return selected , meta

    def strategy_enter_position(self , candle , instrument , meta):

        order = self.broker.OrderRegular(
            instrument,
            meta["action"],
            quantity=self.number_of_lots * instrument.lot_size
        )

        self.orders[instrument] = order
        return order


import talib
from pyalgotrading.strategy import StrategyBase

class EMAPullback(StrategyBase):

    name = "EMA Pullback Momentum"

    def initialize(self):
        self.orders = {}

    def strategy_select_instruments_for_entry(self , candle , bucket):

        selected , meta = [] , []

        for instrument in bucket:

            hist = self.get_historical_data(instrument)

            if hist is None or len(hist) < 60:
                continue

            ema20 = talib.EMA(hist["close"] , 20)
            ema50 = talib.EMA(hist["close"] , 50)

            price = hist["close"].iloc[-1]

            if ema20.iloc[-1] > ema50.iloc[-1] and price < ema20.iloc[-1]:

                selected.append(instrument)
                meta.append({"action":"BUY"})

        return selected , meta

    def strategy_enter_position(self , candle , instrument , meta):

        order = self.broker.OrderRegular(
            instrument,
            meta["action"],
            quantity=self.number_of_lots * instrument.lot_size
        )

        self.orders[instrument] = order
        return order

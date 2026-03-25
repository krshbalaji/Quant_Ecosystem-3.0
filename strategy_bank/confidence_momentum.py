import talib
import numpy as np
from pyalgotrading.strategy import StrategyBase


class InstitutionalMomentumFilter(StrategyBase):

    name = "Institutional Momentum Filter"

    def initialize(self):

        self.orders = {}

    # =========================
    # MARKET HEALTH CHECK
    # =========================

    def market_valid(self , hist):

        close = hist["close"]
        volume = hist["volume"]

        if len(close) < 60:
            return False

        ema20 = talib.EMA(close , 20)
        ema50 = talib.EMA(close , 50)

        atr = talib.ATR(hist["high"], hist["low"], close, timeperiod=14)

        trend_strength = abs(ema20.iloc[-1] - ema50.iloc[-1]) / close.iloc[-1]
        volatility = atr.iloc[-1] / close.iloc[-1]
        participation = volume.iloc[-1] / volume.rolling(20).mean().iloc[-1]

        if trend_strength < 0.002:
            return False

        if volatility < 0.003:
            return False

        if participation < 1.2:
            return False

        return True

    # =========================
    # ENTRY LOGIC
    # =========================

    def strategy_select_instruments_for_entry(self , candle , bucket):

        selected , meta = [] , []

        for instrument in bucket:

            if self.orders.get(instrument):
                continue

            hist = self.get_historical_data(instrument)

            if hist is None:
                continue

            if not self.market_valid(hist):
                continue

            ema20 = talib.EMA(hist["close"] , 20)
            ema50 = talib.EMA(hist["close"] , 50)

            price = hist["close"].iloc[-1]

            # LONG TREND PULLBACK
            if ema20.iloc[-1] > ema50.iloc[-1] and price < ema20.iloc[-1]:

                selected.append(instrument)
                meta.append({"action":"BUY"})

            # SHORT TREND PULLBACK
            elif ema20.iloc[-1] < ema50.iloc[-1] and price > ema20.iloc[-1]:

                selected.append(instrument)
                meta.append({"action":"SELL"})

        return selected , meta

    # =========================
    # EXECUTION
    # =========================

    def strategy_enter_position(self , candle , instrument , meta):

        order = self.broker.OrderRegular(
            instrument,
            meta["action"],
            quantity=self.number_of_lots * instrument.lot_size
        )

        self.orders[instrument] = order
        return order

    # =========================
    # EXIT LOGIC
    # =========================

    def strategy_select_instruments_for_exit(self , candle , bucket):

        selected , meta = [] , []

        for instrument , order in self.orders.items():

            hist = self.get_historical_data(instrument)

            ema20 = talib.EMA(hist["close"] , 20)
            price = hist["close"].iloc[-1]

            if order.order_transaction_type.value == "BUY" and price < ema20.iloc[-1]:

                selected.append(instrument)
                meta.append({"action":"EXIT"})

            elif order.order_transaction_type.value == "SELL" and price > ema20.iloc[-1]:

                selected.append(instrument)
                meta.append({"action":"EXIT"})

        return selected , meta

    def strategy_exit_position(self , candle , instrument , meta):

        if meta["action"] == "EXIT":

            self.orders[instrument].exit_position()
            self.orders[instrument] = None
            return True

        return False
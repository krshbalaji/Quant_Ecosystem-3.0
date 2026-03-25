def generate_strategy(strategy_name, instrument):

    print("\n===== AUTO STRATEGY CODE =====\n")

    if strategy_name == "EMA_PULLBACK":

        print(f"""
import talib
from pyalgotrading.strategy import StrategyBase

class EMA_PULLBACK(StrategyBase):

    name = "EMA Pullback Auto"

    def initialize(self):
        self.orders = {{}}

    def strategy_select_instruments_for_entry(self, candle, bucket):

        selected = []
        meta = []

        for inst in bucket:

            if self.orders.get(inst) is not None:
                continue

            hist = self.get_historical_data(inst)

            if hist is None or len(hist) < 50:
                continue

            ema20 = talib.EMA(hist["close"], timeperiod=20)
            ema50 = talib.EMA(hist["close"], timeperiod=50)

            price = hist["close"].iloc[-1]

            if ema20.iloc[-1] > ema50.iloc[-1] and price < ema20.iloc[-1]:
                selected.append(inst)
                meta.append({{"action":"BUY"}})

            if ema20.iloc[-1] < ema50.iloc[-1] and price > ema20.iloc[-1]:
                selected.append(inst)
                meta.append({{"action":"SELL"}})

        return selected, meta

    def strategy_enter_position(self, candle, inst, meta):

        order = self.broker.OrderRegular(
            inst,
            meta["action"],
            quantity=self.number_of_lots * inst.lot_size
        )

        self.orders[inst] = order
        return order
""")

    elif strategy_name == "ORB_SCALP":

        print(f"""
import talib
from pyalgotrading.strategy import StrategyBase

class ORB_SCALP(StrategyBase):

    name = "ORB Scalper Auto"

    def initialize(self):
        self.orders = {{}}

    def strategy_select_instruments_for_entry(self, candle, bucket):

        selected = []
        meta = []

        for inst in bucket:

            if self.orders.get(inst) is not None:
                continue

            hist = self.get_historical_data(inst)

            if hist is None or len(hist) < 30:
                continue

            high = hist["high"].iloc[-12:].max()
            low = hist["low"].iloc[-12:].min()

            price = hist["close"].iloc[-1]

            if price > high:
                selected.append(inst)
                meta.append({{"action":"BUY"}})

            elif price < low:
                selected.append(inst)
                meta.append({{"action":"SELL"}})

        return selected, meta

    def strategy_enter_position(self, candle, inst, meta):

        order = self.broker.OrderRegular(
            inst,
            meta["action"],
            quantity=self.number_of_lots * inst.lot_size
        )

        self.orders[inst] = order
        return order
""")

    else:
        print("❌ No auto strategy available")


def main():

    strategy = input("Enter Strategy Name: ")
    instrument = input("Enter Instrument: ")

    generate_strategy(strategy, instrument)


if __name__ == "__main__":
    main()
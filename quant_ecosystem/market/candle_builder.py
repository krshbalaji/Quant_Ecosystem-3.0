import pandas as pd

class CandleBuilder:

    def build_from_fyers(self, data):
        candles = []

        for c in data["candles"]:
            candles.append({
                "time": c[0],
                "open": c[1],
                "high": c[2],
                "low": c[3],
                "close": c[4],
                "volume": c[5]
            })

        return candles
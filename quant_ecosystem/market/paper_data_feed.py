import pandas as pd
import numpy as np

class PaperDataFeed:

    def get_candles(self, symbol, interval="1m", limit=100):

        df = pd.DataFrame({
            "open": np.random.random(limit),
            "high": np.random.random(limit),
            "low": np.random.random(limit),
            "close": np.random.random(limit),
            "volume": np.random.randint(100,1000,limit)
        })

        return df
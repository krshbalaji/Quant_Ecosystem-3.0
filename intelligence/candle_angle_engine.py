import numpy as np

class CandleAngleEngine:

    def calculate(self, prices):

        slope = np.polyfit(range(len(prices)), prices, 1)[0]

        return slope
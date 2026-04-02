class CandleAngleEngine:

    def calculate(self, prices):
        if not prices or len(prices) < 2:
            return 0.0

        n = len(prices)
        x_vals = list(range(n))
        y_vals = [float(v) for v in prices]
        x_mean = sum(x_vals) / n
        y_mean = sum(y_vals) / n
        numerator = sum((x_vals[i] - x_mean) * (y_vals[i] - y_mean) for i in range(n))
        denominator = sum((x - x_mean) ** 2 for x in x_vals)
        if denominator == 0:
            return 0.0
        return numerator / denominator

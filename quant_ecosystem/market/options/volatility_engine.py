import math


class VolatilityEngine:

    def log_returns(self, prices):
        if not prices or len(prices) < 2:
            return []

        returns = []

        for i in range(1, len(prices)):
            prev = float(prices[i - 1])
            curr = float(prices[i])

            if prev <= 0 or curr <= 0:
                continue

            returns.append(
                math.log(curr / prev)
            )

        return returns

    def historical_volatility(
        self,
        prices,
        annualization=252,
    ):
        returns = self.log_returns(prices)

        if len(returns) < 2:
            return 0.0

        mean = sum(returns) / len(returns)

        variance = sum(
            (r - mean) ** 2
            for r in returns
        ) / (len(returns) - 1)

        return math.sqrt(
            variance * annualization
        )

    def realized_volatility(
        self,
        intraday_returns,
        annualization=252,
    ):
        if not intraday_returns:
            return 0.0

        variance = sum(
            float(r) ** 2
            for r in intraday_returns
        )

        return math.sqrt(
            variance * annualization
        )

    def implied_volatility(
        self,
        market_price,
        pricing_function,
        initial_guess=0.20,
        tolerance=1e-6,
        max_iter=100,
    ):
        """
        Newton-Raphson IV solver

        pricing_function(vol)
            must return:
            (option_price, vega)
        """

        sigma = float(initial_guess)

        for _ in range(max_iter):
            price, vega = pricing_function(sigma)

            diff = price - market_price

            if abs(diff) < tolerance:
                return sigma

            if abs(vega) < 1e-8:
                break

            sigma = sigma - (diff / vega)

            if sigma <= 0:
                sigma = 1e-4

        return sigma

    def iv_percentile(
        self,
        current_iv,
        iv_history,
    ):
        if not iv_history:
            return 0.0

        iv_history = [
            float(x)
            for x in iv_history
        ]

        below = sum(
            1 for x in iv_history
            if x <= current_iv
        )

        return (
            below / len(iv_history)
        ) * 100.0

    def volatility_regime(
        self,
        current_vol,
        low_threshold=0.15,
        high_threshold=0.30,
    ):
        current_vol = float(current_vol)

        if current_vol < low_threshold:
            return "LOW"

        if current_vol > high_threshold:
            return "HIGH"

        return "NORMAL"


volatility_engine = VolatilityEngine()
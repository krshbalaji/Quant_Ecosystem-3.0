import math


class PortfolioFactorIntelligence:

    def returns(
        self,
        series,
    ):
        if not series or len(series) < 2:
            return []

        result = []

        for i in range(1, len(series)):
            prev = float(series[i - 1])
            curr = float(series[i])

            if prev == 0:
                continue

            result.append(
                (curr - prev) / prev
            )

        return result

    def rolling_volatility(
        self,
        series,
        periods_per_year=252,
    ):
        returns = self.returns(series)

        if not returns:
            return 0.0

        mean = sum(returns) / len(returns)

        variance = sum(
            (r - mean) ** 2
            for r in returns
        ) / len(returns)

        std = math.sqrt(variance)

        return std * math.sqrt(
            periods_per_year
        )

    def beta(
        self,
        asset_series,
        benchmark_series,
    ):
        asset_returns = self.returns(
            asset_series
        )

        benchmark_returns = self.returns(
            benchmark_series
        )

        n = min(
            len(asset_returns),
            len(benchmark_returns),
        )

        if n == 0:
            return 0.0

        asset_returns = asset_returns[:n]
        benchmark_returns = benchmark_returns[:n]

        asset_mean = (
            sum(asset_returns) / n
        )

        benchmark_mean = (
            sum(benchmark_returns) / n
        )

        covariance = sum(
            (
                asset_returns[i]
                - asset_mean
            )
            * (
                benchmark_returns[i]
                - benchmark_mean
            )
            for i in range(n)
        ) / n

        benchmark_variance = sum(
            (
                r - benchmark_mean
            ) ** 2
            for r in benchmark_returns
        ) / n

        if benchmark_variance == 0:
            return 0.0

        return covariance / benchmark_variance

    def momentum(
        self,
        series,
        lookback=5,
    ):
        if (
            not series
            or len(series) <= lookback
        ):
            return 0.0

        start = float(
            series[-lookback - 1]
        )

        end = float(series[-1])

        if start == 0:
            return 0.0

        return (
            (end - start) / start
        ) * 100.0

    def rolling_correlation(
        self,
        series_a,
        series_b,
    ):
        a = self.returns(series_a)
        b = self.returns(series_b)

        n = min(len(a), len(b))

        if n == 0:
            return 0.0

        a = a[:n]
        b = b[:n]

        mean_a = sum(a) / n
        mean_b = sum(b) / n

        cov = sum(
            (a[i] - mean_a)
            * (b[i] - mean_b)
            for i in range(n)
        )

        std_a = math.sqrt(sum(
            (x - mean_a) ** 2
            for x in a
        ))

        std_b = math.sqrt(sum(
            (x - mean_b) ** 2
            for x in b
        ))

        if std_a == 0 or std_b == 0:
            return 0.0

        return cov / (std_a * std_b)

    def correlation_clusters(
        self,
        series_map,
        threshold=0.75,
    ):
        symbols = list(series_map.keys())
        clusters = []

        visited = set()

        for sym in symbols:
            if sym in visited:
                continue

            cluster = [sym]
            visited.add(sym)

            for other in symbols:
                if other == sym:
                    continue

                if other in visited:
                    continue

                corr = self.rolling_correlation(
                    series_map[sym],
                    series_map[other],
                )

                if corr >= threshold:
                    cluster.append(other)
                    visited.add(other)

            clusters.append(cluster)

        return clusters


portfolio_factor_intelligence = (
    PortfolioFactorIntelligence()
)
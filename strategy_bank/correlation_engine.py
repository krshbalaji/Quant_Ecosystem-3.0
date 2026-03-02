class CorrelationEngine:

    def correlation_matrix(self, strategy_reports):
        matrix = {}
        for left in strategy_reports:
            matrix[left["id"]] = {}
            left_returns = left["metrics"].get("returns", [])
            for right in strategy_reports:
                right_returns = right["metrics"].get("returns", [])
                matrix[left["id"]][right["id"]] = self._corr(left_returns, right_returns)
        return matrix

    def correlated_pairs(self, matrix, threshold):
        pairs = []
        keys = sorted(matrix.keys())
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                left = keys[i]
                right = keys[j]
                value = matrix[left][right]
                if abs(value) >= threshold:
                    pairs.append((left, right, value))
        return pairs

    def _corr(self, left, right):
        n = min(len(left), len(right))
        if n < 5:
            return 0.0

        a = left[-n:]
        b = right[-n:]
        mean_a = sum(a) / n
        mean_b = sum(b) / n

        num = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(n))
        den_a = sum((item - mean_a) ** 2 for item in a) ** 0.5
        den_b = sum((item - mean_b) ** 2 for item in b) ** 0.5
        if den_a == 0 or den_b == 0:
            return 0.0
        return round(num / (den_a * den_b), 4)

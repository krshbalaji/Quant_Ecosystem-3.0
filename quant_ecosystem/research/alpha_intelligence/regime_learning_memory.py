class RegimeLearningMemory:

    def __init__(self):

        self.memory = {
            "trend": [],
            "mean": [],
            "volatile": []
        }

    def record(self, regime, fitness):

        self.memory[regime].append(fitness)

        if len(self.memory[regime]) > 500:
            self.memory[regime] = self.memory[regime][-500:]

    def regime_score(self, regime):

        data = self.memory.get(regime, [])

        if not data:
            return 0

        return sum(data) / len(data)
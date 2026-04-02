class TestStrategy:

    def __init__(self, **kwargs):
        self.id = "test_strategy"
        self.name = "Test Strategy"
        self.timeframe = "5m"

    def generate_signal(self, data):
        return None

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "timeframe": self.timeframe,
            "strategy": self
        }
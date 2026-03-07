class SystemIntegrityCheck:

    def __init__(self, router):
        self.router = router

    def run_all(self):

        results = {
            "config": self.check_config(),
            "data_engine": self.check_market_data(),
            "execution_router": self.check_execution(),
            "strategy_engine": self.check_strategy(),
            "telegram": self.check_telegram(),
        }

        self.auto_heal(results)

        return results
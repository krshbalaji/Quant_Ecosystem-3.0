class RegimeSurvivalController:

    def __init__(self, execution_bridge):

        self.exec = execution_bridge

    def adjust(self, regime):

        if regime == "TREND_STRONG":
            self.exec.MAX_ACTIVE_TRADES = 4
            self.exec.TRADE_COOLDOWN = 1

        elif regime == "CHOP":
            self.exec.MAX_ACTIVE_TRADES = 2
            self.exec.TRADE_COOLDOWN = 4

        elif regime == "PANIC":
            self.exec.MAX_ACTIVE_TRADES = 1
            self.exec.TRADE_COOLDOWN = 7
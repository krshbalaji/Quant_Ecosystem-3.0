import random


class RegimeSurvivalReal:

    def __init__(self, execution_bridge, alpha_book):

        self.exec = execution_bridge
        self.alpha_book = alpha_book

    # -----------------------------------------
    # MAIN SURVIVAL ADJUSTMENT
    # -----------------------------------------

    def adjust(self, regime):

        if regime == "TREND_STRONG":

            self.exec.MAX_ACTIVE_TRADES = 4
            self.exec.TRADE_COOLDOWN = 1

            for g in self.alpha_book.live_alphas:
                g.alpha_confidence = min(
                    1.0,
                    getattr(g, "alpha_confidence", 0.5) + 0.05
                )

        elif regime == "CHOP":

            self.exec.MAX_ACTIVE_TRADES = 2
            self.exec.TRADE_COOLDOWN = 4

            for g in self.alpha_book.live_alphas:
                g.alpha_confidence *= 0.9

        elif regime == "PANIC":

            self.exec.MAX_ACTIVE_TRADES = 1
            self.exec.TRADE_COOLDOWN = 7

            survivors = []

            for g in self.alpha_book.live_alphas:

                if random.random() > 0.5:
                    survivors.append(g)

            self.alpha_book.live_alphas[:] = survivors
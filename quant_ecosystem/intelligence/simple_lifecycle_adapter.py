class SimpleLifecycleAdapter:

    def __init__(self, alpha_book, execution_bridge):

        self.alpha_book = alpha_book
        self.exec = execution_bridge

        self.age = {}

    def update(self):

        survivors = []

        for g in self.alpha_book.live_alphas:

            self.age[g] = self.age.get(g, 0) + 1

            score = self.exec.alpha_score.get(g, 0)

            if score < -15:
                print(f"[LIFECYCLE] killed weak alpha {g.family} {g.symbol}")
                continue

            if self.age[g] > 8:
                print(f"[LIFECYCLE] expired alpha {g.family} {g.symbol}")
                continue

            survivors.append(g)

        self.alpha_book.live_alphas[:] = survivors
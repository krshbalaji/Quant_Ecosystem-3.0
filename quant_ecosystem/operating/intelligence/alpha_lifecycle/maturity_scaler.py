class MaturityScaler:

    def scale_factor(self, genome, alpha_state):

        age = alpha_state.age.get(genome, 1)
        pnl = alpha_state.pnl.get(genome, 0)

        base = min(2.0, age / 10)

        if pnl > 0:
            return base

        return base * 0.6
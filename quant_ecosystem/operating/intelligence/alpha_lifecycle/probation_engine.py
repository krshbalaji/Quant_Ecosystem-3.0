class ProbationEngine:

    def allow_scale(self, genome, alpha_state):

        age = alpha_state.age.get(genome, 0)
        pnl = alpha_state.pnl.get(genome, 0)

        if age < 5:
            return False

        if pnl < 0:
            return False

        return True
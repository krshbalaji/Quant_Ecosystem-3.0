class RetirementEngine:

    def should_retire(self, genome, alpha_state):

        pnl = alpha_state.pnl.get(genome, 0)
        age = alpha_state.age.get(genome, 0)

        if age > 30 and pnl < -3:
            return True

        return False
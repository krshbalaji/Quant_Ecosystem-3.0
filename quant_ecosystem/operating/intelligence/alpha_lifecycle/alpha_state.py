class AlphaState:

    def __init__(self):
        self.state = {}
        self.age = {}
        self.pnl = {}
        self.scale = {}

    def get(self, genome):
        return self.state.get(genome, "NEW")

    def set(self, genome, new_state):
        self.state[genome] = new_state

    def increment_age(self, genome):
        self.age[genome] = self.age.get(genome, 0) + 1

    def update_pnl(self, genome, pnl):
        self.pnl[genome] = self.pnl.get(genome, 0) + pnl
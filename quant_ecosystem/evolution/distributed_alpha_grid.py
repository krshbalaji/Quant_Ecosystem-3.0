class DistributedAlphaGrid:

    def __init__(self, alpha_factory, **kwargs):

        self.alpha_factory = alpha_factory

    def run_cycle(self):

        print("Distributed Alpha Grid running...")

        evolved = self.alpha_factory.evolve()

        return evolved
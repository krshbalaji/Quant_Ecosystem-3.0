import random


class AlphaEvolutionEngine:

    def __init__(self, discovery_engine, mutation_engine):

        self.discovery = discovery_engine
        self.mutation = mutation_engine

    def evolve(self, elite_genomes):

        mutated = self.mutation.mutate_batch(elite_genomes)

        fresh = self.discovery.discover(batch_size=20)

        return mutated + fresh
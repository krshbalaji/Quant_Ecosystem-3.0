"""Mutation engine micro-layer adapter."""


class MutationEngineLayer:
    """Facade over mutation engine with explicit safety behavior."""

    def __init__(self, mutation_engine=None, **kwargs):
        self.mutation_engine = mutation_engine

    def is_enabled(self):
        return bool(self.mutation_engine and getattr(self.mutation_engine, "enabled", False))

    def run(self, strategy_rows):
        if not self.is_enabled():
            return []
        return self.mutation_engine.run_daily(strategy_rows)

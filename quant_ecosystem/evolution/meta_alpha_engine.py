class MetaAlphaEngine:

    def __init__(self, strategy_registry):
        self.strategy_registry = strategy_registry

    def build_meta_strategy(self):

        strategies = self.strategy_registry.get_all()

        if not strategies:
            return None

        meta = {
            "type": "meta_alpha",
            "components": strategies[:5]
        }

        return meta
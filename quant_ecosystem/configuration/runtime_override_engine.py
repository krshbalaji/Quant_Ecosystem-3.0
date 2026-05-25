from copy import deepcopy


class RuntimeOverrideEngine:

    def apply(
        self,
        config,
        **overrides,
    ):
        cfg = deepcopy(config)

        for key, value in overrides.items():
            if hasattr(cfg, key):
                setattr(cfg, key, value)

        return cfg


runtime_override_engine = (
    RuntimeOverrideEngine()
)
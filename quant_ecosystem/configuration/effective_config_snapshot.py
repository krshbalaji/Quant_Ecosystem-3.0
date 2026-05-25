from dataclasses import asdict


class EffectiveConfigSnapshot:

    def snapshot(
        self,
        config,
    ):
        return asdict(config)


effective_config_snapshot = (
    EffectiveConfigSnapshot()
)
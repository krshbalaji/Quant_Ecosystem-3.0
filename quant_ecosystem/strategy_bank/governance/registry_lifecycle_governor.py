class RegistryLifecycleGovernor:
    """
    Institutional sovereign authority over strategy lifecycle.
    LifecycleManager emits signals.
    Governor emits final state decisions.
    """

    def __init__(
        self,
        registry=None,
        config=None,
    ):
        self.registry = registry
        self.config = config

    def decide_stage(
        self,
        row,
        candidate_stage,
        regime,
        ranked_universe=None,
    ):
        stage = str(candidate_stage).upper()

        # --- hard terminal protection ---
        if str(row.get("stage")).upper() == "RETIRED":
            return "RETIRED"

        # --- regime incompatibility freeze ---
        pref = row.get("regime_preference", [])

        if pref and regime not in pref:
            if stage == "LIVE":
                return "SHADOW"

        # --- diversity preservation ---
        if ranked_universe:
            live_count = sum(
                1
                for r in ranked_universe
                if str(r.get("stage")).upper() == "LIVE"
            )

            if live_count > 8 and stage == "LIVE":
                return "SHADOW"

        row["stage"] = stage

        if self.registry:
            self.registry.upsert(
                row,
                source="governor",
            )

        return stage
from quant_ecosystem.persistence.in_memory_event_store import (
    event_store,
)


class ReplayRecoveryEngine:

    def rebuild_state(
        self,
    ):
        reconstructed = {}

        for event in (
            event_store.all_events()
        ):
            event_type = (
                event["event_type"]
            )

            payload = (
                event["payload"]
            )

            reconstructed[
                event_type
            ] = payload

        return reconstructed

    def replay_count(
        self,
    ):
        return len(
            event_store.all_events()
        )


replay_recovery_engine = (
    ReplayRecoveryEngine()
)
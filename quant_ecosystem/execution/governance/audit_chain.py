from quant_ecosystem.execution.sovereignty.state_store import (
    sovereign_state_store,
)


class AuditChain:

    def append(
        self,
        payload,
    ):
        return (
            sovereign_state_store
            .append_audit_event(
                payload
            )
        )

    def verify(self):
        return (
            sovereign_state_store
            .verify_audit_chain()
        )


audit_chain = AuditChain()
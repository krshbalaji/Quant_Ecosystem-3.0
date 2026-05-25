from quant_ecosystem.release.capability_registry import (
    capability_registry,
)


class InstitutionalAudit:

    def audit(self):
        caps = (
            capability_registry.capabilities()
        )

        return {
            "capability_count": len(caps),
            "healthy": len(caps) >= 10,
        }


institutional_audit = (
    InstitutionalAudit()
)
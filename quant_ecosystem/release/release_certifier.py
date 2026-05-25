from quant_ecosystem.release.institutional_audit import (
    institutional_audit,
)


class ReleaseCertifier:

    def certify(self):
        audit = institutional_audit.audit()

        return audit["healthy"] is True


release_certifier = (
    ReleaseCertifier()
)
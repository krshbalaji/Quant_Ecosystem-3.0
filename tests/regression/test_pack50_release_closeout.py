from quant_ecosystem.release import (
    capability_registry,
    institutional_audit,
    release_certifier,
    QE3_VERSION,
    version,
)


def test_capabilities():
    caps = (
        capability_registry.capabilities()
    )

    assert "api" in caps
    assert "deployment" in caps


def test_audit():
    result = institutional_audit.audit()

    assert result["healthy"] is True


def test_certification():
    assert (
        release_certifier.certify()
        is True
    )


def test_version_constant():
    assert QE3_VERSION.startswith("1.")


def test_version_function():
    assert version() == QE3_VERSION
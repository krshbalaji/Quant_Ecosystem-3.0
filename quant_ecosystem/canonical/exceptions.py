"""
QE3 Canonical Layer Exceptions
Pack19 — Unified Data Canonicalization Layer
"""


class CanonicalizationError(Exception):
    """Base canonicalization exception."""
    pass


class UnsupportedProviderError(CanonicalizationError):
    """Provider not supported by canonical router."""
    pass


class InvalidPayloadError(CanonicalizationError):
    """Malformed provider payload."""
    pass


class MissingRequiredFieldError(CanonicalizationError):
    """Required provider field missing."""
    pass


class SchemaValidationError(CanonicalizationError):
    """Canonical schema validation failed."""
    pass


class TypeCoercionError(CanonicalizationError):
    """Failed to coerce provider payload type."""
    pass


class TimestampNormalizationError(CanonicalizationError):
    """Timestamp normalization failed."""
    pass


class UnsupportedFeatureCanonicalizationError(CanonicalizationError):
    """Feature canonicalization not implemented."""
    pass
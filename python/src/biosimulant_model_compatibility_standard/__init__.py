"""Python reference implementation of the Biosimulant Model Compatibility Standard."""

from .bundle import Bundle, get_bundle
from .canonical import canonical_bytes, digest
from .compare import compare_contracts
from .locks import build_compatibility_lock
from .normalization import normalize_contract, normalize_manifest
from .resolution import ResolutionLimits, resolve_contracts
from .security import DEFAULT_RESOURCE_LIMITS, ResourceLimitError, ResourceLimits, ensure_json_limits
from .validation import ValidationFinding, validate_contract, validate_manifest, validate_object

__all__ = [
    "Bundle",
    "ValidationFinding",
    "build_compatibility_lock",
    "canonical_bytes",
    "compare_contracts",
    "digest",
    "get_bundle",
    "normalize_contract",
    "normalize_manifest",
    "ResolutionLimits",
    "DEFAULT_RESOURCE_LIMITS",
    "ResourceLimitError",
    "ResourceLimits",
    "ensure_json_limits",
    "resolve_contracts",
    "validate_contract",
    "validate_manifest",
    "validate_object",
]

__version__ = "0.0.1"

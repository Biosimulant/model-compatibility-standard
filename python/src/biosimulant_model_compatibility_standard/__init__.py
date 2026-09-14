"""Reference implementation for the BioSimulant Model Compatibility Standard."""

from .bundle import Bundle, get_bundle
from .canonical import canonical_bytes, digest
from .compare import compare_contracts
from .locks import build_compatibility_lock
from .normalization import normalize_contract, normalize_manifest
from .validation import ValidationFinding, validate_contract, validate_manifest

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
    "validate_contract",
    "validate_manifest",
]

__version__ = "0.1.0a1"

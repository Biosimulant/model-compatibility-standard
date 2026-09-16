from __future__ import annotations

from .catalogue import (
    StandardError,
    catalogue_digest,
    get_profile,
    list_profiles,
    load_standard,
    profile_digest,
)

STANDARD_ID = "biosimulant.model-compatibility"
STANDARD_VERSION = "0"
CATALOGUE_VERSION = "0.1.0"

CATALOGUE_SHA256 = catalogue_digest()

__all__ = [
    "CATALOGUE_SHA256",
    "CATALOGUE_VERSION",
    "STANDARD_ID",
    "STANDARD_VERSION",
    "StandardError",
    "catalogue_digest",
    "get_profile",
    "list_profiles",
    "load_standard",
    "profile_digest",
]

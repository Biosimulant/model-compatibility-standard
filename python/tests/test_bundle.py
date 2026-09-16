import shutil

import pytest

from biosimulant_model_compatibility_standard import Bundle, get_bundle, validate_object


def test_catalogue_counts_and_active_profiles_load():
    bundle = get_bundle()
    profiles = list(bundle.profiles())
    assert bundle.catalogue["counts"]["profiles"] == len(profiles)
    assert bundle.catalogue["counts"]["fields"] > 0
    assert profiles
    assert len({profile["profile_id"] for profile in profiles}) == len(profiles)
    assert all(profile["$id"] in bundle.profile_index for profile in profiles)
    reviewed = sum(profile["release_eligible"] for profile in profiles)
    remaining = len(profiles) - reviewed
    assert bundle.catalogue["review_counts"] == {
        "reviewed": reviewed,
        "remaining": remaining,
    }
    ready = sum(
        profile["technical_pre_review"]["status"] == "ready-for-external-review"
        for profile in profiles
    )
    assert bundle.catalogue["technical_pre_review_counts"] == {
        "ready_for_external_review": ready,
        "needs_work": len(profiles) - ready,
    }
    assert bundle.manifest["ga_ready"] is (remaining == 0)
    expected_blockers = [] if remaining == 0 else [
        f"{remaining} profiles still need complete, independent scientific and schema review evidence."
    ]
    assert bundle.manifest["ga_blockers"] == expected_blockers


def test_every_profile_has_a_distinct_typed_review_packet():
    bundle = get_bundle()
    concepts = set()
    for profile in bundle.profiles():
        assert validate_object(profile, "profile-definition.schema.json", bundle=bundle) == []
        concept = profile["fixed"]["semantic"]["concept"]
        assert concept not in concepts
        concepts.add(concept)
        assert profile["allowed"]["representation"]["kind"]
        assert profile["review_questions"]
        for requirement in profile["requirements"]:
            assert requirement["schema"]
            assert requirement["schema"].get("type") != [
                "string", "number", "integer", "boolean", "array", "object", "null"
            ]
        packet = bundle.read_json(
            f"review-packets/{profile['domain']}/{profile['name']}.json"
        )
        assert validate_object(packet, "profile-review-packet.schema.json", bundle=bundle) == []
        assert packet["profile_sha256"] == bundle.profile_index[profile["$id"]]["sha256"]
        assert packet["internal_quality_errors"] == []
        assert packet["technical_pre_review"]["scientific_signoff_required"] is True
    assert len(concepts) == bundle.catalogue["counts"]["profiles"]
    internal = bundle.read_json("catalogue/internal-validation.json")
    assert validate_object(internal, "internal-validation.schema.json", bundle=bundle) == []


def test_manifest_lists_every_generated_file_with_digest():
    bundle = get_bundle()
    assert bundle.manifest["counts"]["profiles"] == bundle.catalogue["counts"]["profiles"]
    assert bundle.digest.startswith("sha256:")
    assert len(bundle.digest) == 71
    bundle.verify_integrity()


def test_bundle_integrity_detects_tampering(tmp_path):
    original = get_bundle()
    root = tmp_path / "v0.1"
    shutil.copytree(original.root, root)
    target = root / "rules" / "operators.json"
    target.write_bytes(target.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="size does not match"):
        Bundle(root).verify_integrity()


def test_term_registry_is_published_and_version_independent():
    from biosimulant_model_compatibility_standard import get_bundle

    bundle = get_bundle()
    registry = bundle.read_json("catalogue/terms.json")
    expected = bundle.catalogue["counts"]["profiles"]
    assert registry["count"] == expected
    assert len(registry["terms"]) == expected
    ids = [term["id"] for term in registry["terms"]]
    assert len(set(ids)) == expected
    # A term must outlive the profile version that minted it, or a v0.2 profile would report every
    # v0.1 port as incompatible even where the meaning is unchanged.
    assert [term for term in ids if "/v0." in term] == []
    assert all(term["label"] and term["definition"] for term in registry["terms"])
    # External terms remain empty until a reviewer decides whether an exact maintained term exists.
    assert all(term["external_terms"] == [] for term in registry["terms"])

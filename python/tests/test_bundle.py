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
    assert all(profile["status"] in {"active", "deprecated"} for profile in profiles)
    assert all(profile["sources"] for profile in profiles)
    assert all(profile["examples"] for profile in profiles)


def test_every_profile_is_a_complete_distinct_contract():
    bundle = get_bundle()
    concepts = set()
    for profile in bundle.profiles():
        assert validate_object(profile, "profile-definition.schema.json", bundle=bundle) == []
        concept = profile["fixed"]["semantic"]["concept"]
        assert concept not in concepts
        concepts.add(concept)
        assert profile["allowed"]["representation"]["kind"]
        assert {decision["disposition"] for decision in profile["field_dispositions"].values()} <= {
            "required", "conditional", "recommended", "excluded"
        }
        assert all(source["title"] and source["url"] for source in profile["sources"])
        for requirement in profile["requirements"]:
            assert requirement["schema"]
            assert requirement["schema"].get("type") != [
                "string", "number", "integer", "boolean", "array", "object", "null"
            ]
    assert len(concepts) == bundle.catalogue["counts"]["profiles"]


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
    # External terms remain empty until an exact maintained term is adopted in a profile change.
    assert all(term["external_terms"] == [] for term in registry["terms"])

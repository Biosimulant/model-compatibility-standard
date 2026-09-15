import shutil

import pytest

from biosimulant_model_compatibility_standard import Bundle, get_bundle, validate_object


def test_catalogue_counts_and_all_profiles_load():
    bundle = get_bundle()
    assert bundle.catalogue["counts"] == {
        "profiles": 650,
        "item_definitions": 267,
        "item_packs": 30,
    }
    profiles = list(bundle.profiles())
    assert len(profiles) == 650
    assert all(profile["$id"] in bundle.profile_index for profile in profiles)
    assert not any(profile["release_eligible"] for profile in profiles)
    assert bundle.catalogue["review_counts"] == {"reviewed": 0, "remaining": 650}
    assert bundle.catalogue["technical_pre_review_counts"] == {
        "ready_for_external_review": 650,
        "needs_work": 0,
    }
    assert all(
        profile["technical_pre_review"]["status"] == "ready-for-external-review"
        for profile in profiles
    )
    assert bundle.manifest["ga_ready"] is False
    assert bundle.manifest["ga_blockers"] == [
        "650 profiles still need complete, independent scientific and schema review evidence."
    ]


def test_every_profile_has_a_distinct_typed_review_packet():
    bundle = get_bundle()
    concepts = set()
    for profile in bundle.profiles():
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
    assert len(concepts) == 650
    internal = bundle.read_json("catalogue/internal-validation.json")
    assert validate_object(internal, "internal-validation.schema.json", bundle=bundle) == []


def test_manifest_lists_every_generated_file_with_digest():
    bundle = get_bundle()
    assert bundle.manifest["counts"]["profiles"] == 650
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

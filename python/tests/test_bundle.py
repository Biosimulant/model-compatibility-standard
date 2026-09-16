import shutil

import pytest

from biosimulant_model_compatibility_standard import Bundle, get_bundle, validate_object


def test_catalogue_counts_and_active_profiles_load():
    bundle = get_bundle()
    profiles = list(bundle.profiles())
    assert bundle.catalogue["counts"]["profiles"] == len(profiles)
    assert bundle.catalogue["counts"]["item_definitions"] > 0
    assert bundle.catalogue["counts"]["item_packs"] > 0
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
    # v0.1 port as incompatible even where the meaning is unchanged (decision D3).
    assert [term for term in ids if "/v0." in term] == []
    assert all(term["label"] and term["definition"] for term in registry["terms"])
    # External terms are an honest absence until a reviewer decides per profile (erratum E3).
    assert all(term["external_terms"] == [] for term in registry["terms"])


def test_role_typed_taxa_vocabulary_is_published():
    from biosimulant_model_compatibility_standard import get_bundle

    bundle = get_bundle()
    items = {item["path"]: item for item in bundle.read_json("catalogue/items.json")["items"]}
    member = items["biological_context.taxa"]["json_schema"]["items"]
    # A single species field cannot describe a host and its pathogen, or the members of a community,
    # so a port declares each organism and what it is to the measurement (decision D5). No profile
    # requires this yet, so nothing else pins the vocabulary.
    assert member["required"] == ["taxon", "role"]
    assert member["properties"]["role"]["enum"] == ["host", "pathogen", "community_member", "donor"]
    assert member["properties"]["taxon"]["pattern"] == "^NCBITaxon:[1-9][0-9]*$"
    assert items["biological_context.taxa[].role"]["json_schema"] == member["properties"]["role"]
    assert items["biological_context.taxa[].taxon"]["json_schema"] == member["properties"]["taxon"]
    # The order organisms are listed in carries no meaning.
    set_paths = bundle.read_json("rules/normalization.json")["set_like_paths"]
    assert "/contract/biological_context/taxa" in set_paths

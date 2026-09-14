from biosimulant_model_compatibility_standard import get_bundle


def test_catalogue_counts_and_all_profiles_load():
    bundle = get_bundle()
    assert bundle.catalogue["counts"] == {
        "profiles": 650,
        "item_definitions": 266,
        "item_packs": 30,
    }
    profiles = list(bundle.profiles())
    assert len(profiles) == 650
    assert all(profile["$id"] in bundle.profile_index for profile in profiles)
    assert not any(profile["release_eligible"] for profile in profiles)


def test_manifest_lists_every_generated_file_with_digest():
    bundle = get_bundle()
    assert bundle.manifest["counts"]["profiles"] == 650
    assert bundle.digest.startswith("sha256:")
    assert len(bundle.digest) == 71

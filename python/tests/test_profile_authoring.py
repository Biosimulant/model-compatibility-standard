import importlib.util
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "build_standard", ROOT / "scripts" / "build_standard.py"
)
assert SPEC is not None and SPEC.loader is not None
build_standard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build_standard)


def test_yaml_source_rejects_duplicate_keys():
    with pytest.raises(ValueError, match="duplicate YAML key"):
        yaml.load(
            "fields:\n  semantic.concept: required\n  semantic.concept: excluded\n",
            Loader=build_standard.UniqueKeyLoader,
        )


def test_authored_profiles_have_sources_and_final_field_decisions():
    build_standard.load_declarations()
    fields = build_standard.load_fields()
    build_standard.FIELD_INDEX.clear()
    build_standard.FIELD_INDEX.update(
        {
            field["path"]: {
                **field,
                "comparison_operator": field["comparison"],
                "json_schema": field["schema"],
            }
            for field in fields
        }
    )

    profiles = build_standard.load_profiles()
    assert profiles
    for profile in profiles:
        assert profile["status"] in {"active", "deprecated"}
        assert profile["sources"]
        assert profile["examples"]
        assert {
            decision["disposition"] for decision in profile["field_dispositions"].values()
        } <= build_standard.FIELD_DISPOSITIONS
        for path in profile["fixed_values"]:
            assert profile["field_dispositions"][path]["disposition"] == "required"

    smiles = next(profile for profile in profiles if profile["id"] == "chemical/molecular-smiles@0.1")
    assert build_standard.profile_fixed(smiles)["representation"]["structure_format"] == "smiles"
    syntax = build_standard.FIELD_INDEX["representation.syntax_features"]
    assert syntax["comparison_operator"] == "subset"
    assert syntax["ordered"] is False

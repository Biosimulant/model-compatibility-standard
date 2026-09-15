import importlib.util
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "build_standard", ROOT / "scripts" / "build_standard.py"
)
assert SPEC is not None and SPEC.loader is not None
build_standard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build_standard)
applicable_review_sections = build_standard.applicable_review_sections
review_evidence_errors = build_standard.review_evidence_errors
required_fixture_groups = build_standard.required_fixture_groups


def test_review_template_matches_its_json_schema():
    schema = json.loads((ROOT / "source" / "profile-review.schema.json").read_text())
    template = json.loads(
        (ROOT / "source" / "reviews" / "profile-review.template.json").read_text()
    )
    errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(template))
    assert errors == []


def _profile():
    catalogue = json.loads((ROOT / "source" / "catalogue.review.json").read_text())
    return catalogue["profiles"][0]


def _valid_evidence(profile):
    source_id = "doi:10.0000/example"
    return {
        "profile_id": profile["id"],
        "authors": ["Profile Author"],
        "scientific_reviewer": "Scientific Reviewer",
        "schema_reviewer": "Schema Reviewer",
        "domain_owner": "Domain Owner",
        "reviewed_at": "2026-09-15",
        "sources": [
            {
                "id": source_id,
                "title": "Example authoritative source",
                "kind": "standard",
                "url": "https://example.org/source",
                "version": "1.0",
                "sha256": "sha256:" + ("1" * 64),
            }
        ],
        "intended_use": "Checks scalar quantity ports with an explicitly declared meaning.",
        "limitations": ["It does not prove that the producing model is scientifically valid."],
        "decisions": {
            section: {
                "disposition": "included",
                "rationale": f"The {section} fields are needed to compare this kind of port safely.",
                "field_paths": [f"{section}.example"],
                "source_ids": [source_id],
            }
            for section in applicable_review_sections(profile)
        },
        "fixture_review": required_fixture_groups(profile),
    }


def test_complete_independent_review_is_eligible():
    profile = _profile()
    assert review_evidence_errors(profile, _valid_evidence(profile)) == []


def test_profile_author_cannot_approve_own_scientific_review():
    profile = _profile()
    evidence = _valid_evidence(profile)
    evidence["scientific_reviewer"] = "Profile Author"
    assert "scientific_reviewer must not be one of the profile authors" in review_evidence_errors(
        profile, evidence
    )


def test_every_applicable_section_needs_a_sourced_decision():
    profile = _profile()
    evidence = _valid_evidence(profile)
    evidence["decisions"] = {}
    errors = review_evidence_errors(profile, evidence)
    assert any(message.startswith("decisions are missing:") for message in errors)

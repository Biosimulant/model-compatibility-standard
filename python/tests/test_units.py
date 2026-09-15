"""Unit engine: parsing UCUM expressions and deciding whether two units convert.

These test the prototype for decision D1 in isolation. It is not yet wired into comparison, so
the scientific checks for units remain open defects until it is.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from biosimulant_model_compatibility_standard.units import UnitError, convert, parse

ROOT = Path(__file__).resolve().parents[2]
TABLE = json.loads((ROOT / "source" / "vendor" / "ucum" / "ucum-table.json").read_text(encoding="utf-8"))


def factor(source: str, target: str) -> float:
    conversion = convert(source, target, TABLE)
    assert conversion is not None, f"{source} -> {target} should convert"
    return conversion.factor


def test_table_is_built_from_the_pinned_ucum_release() -> None:
    lock = json.loads((ROOT / "docs" / "scientific-remediation" / "sources" / "sources.lock.json").read_text(encoding="utf-8"))
    pinned = next(entry for entry in lock["sources"] if entry["id"] == "ucum-2.2")
    assert TABLE["ucum"]["sha256"] == pinned["sha256"]
    assert TABLE["ucum"]["version"] == "2.2"


@pytest.mark.parametrize(("source", "target", "expected"), [
    ("g", "kg", 1e-3),
    ("kg", "g", 1e3),
    ("1/s", "/min", 60.0),
    ("mL", "L", 1e-3),
    ("umol/L", "mmol/L", 1e-3),
    ("d", "s", 86400.0),
    ("mo", "d", 30.4375),
    ("a", "d", 365.25),
])
def test_same_quantity_converts_by_an_exact_factor(source: str, target: str, expected: float) -> None:
    assert factor(source, target) == pytest.approx(expected)


def test_mercury_pressure_converts_to_kilopascals() -> None:
    assert factor("mm[Hg]", "kPa") == pytest.approx(0.133322, rel=1e-5)


def test_celsius_and_kelvin_are_related_by_an_offset() -> None:
    conversion = convert("Cel", "K", TABLE)
    assert conversion is not None and conversion.affine
    assert conversion.factor == pytest.approx(1.0) and conversion.offset == pytest.approx(273.15)


def test_fahrenheit_converts_to_celsius() -> None:
    conversion = convert("[degF]", "Cel", TABLE)
    assert conversion is not None
    assert 32 * conversion.factor + conversion.offset == pytest.approx(0.0, abs=1e-9)
    assert 212 * conversion.factor + conversion.offset == pytest.approx(100.0)


def test_v01_molar_spellings_resolve_through_deprecated_aliases() -> None:
    assert factor("uM", "mol/L") == pytest.approx(1e-6)
    assert factor("nM", "uM") == pytest.approx(1e-3)


@pytest.mark.parametrize(("source", "target"), [("mg", "s"), ("kg", "s"), ("mg/L", "umol/L")])
def test_different_dimensions_do_not_convert(source: str, target: str) -> None:
    assert convert(source, target, TABLE) is None


@pytest.mark.parametrize(("source", "target"), [
    ("[PFU]/mL", "[TCID_50]/mL"),
    ("[IU]/mL", "{BAU}/mL"),
    ("Cel/min", "K/min"),
    ("fmol/(cell.h)", "fmol/h"),
])
def test_undecidable_pairs_raise_rather_than_pass(source: str, target: str) -> None:
    with pytest.raises(UnitError):
        convert(source, target, TABLE)


def test_a_multi_digit_number_is_one_factor() -> None:
    assert parse("86400", TABLE).factor == pytest.approx(86400.0)


def test_dimension_alone_cannot_tell_frequency_from_radioactivity() -> None:
    # A known limit of dimensional analysis, and the reason D1 requires quantity kinds.
    assert factor("Hz", "Bq") == pytest.approx(1.0)

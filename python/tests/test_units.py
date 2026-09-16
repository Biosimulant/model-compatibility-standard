"""Unit engine: parsing UCUM expressions and deciding whether two units convert."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pytest

from biosimulant_model_compatibility_standard.units import UnitError, convert_unit, parse_unit

ROOT = Path(__file__).resolve().parents[2]
TABLE = json.loads((ROOT / "source" / "vendor" / "ucum" / "ucum-table.json").read_text(encoding="utf-8"))


def factor(source: str, target: str) -> float:
    conversion = convert_unit(source, target, TABLE)
    assert conversion is not None, f"{source} -> {target} should convert"
    return conversion.factor


def test_table_is_built_from_the_pinned_ucum_release() -> None:
    source = ROOT / "source" / "vendor" / "ucum" / "ucum-essence.xml"
    assert TABLE["ucum"]["sha256"] == "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest()
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
    conversion = convert_unit("Cel", "K", TABLE)
    assert conversion is not None and conversion.affine
    assert conversion.factor == pytest.approx(1.0) and conversion.offset == pytest.approx(273.15)


def test_fahrenheit_converts_to_celsius() -> None:
    conversion = convert_unit("[degF]", "Cel", TABLE)
    assert conversion is not None
    assert 32 * conversion.factor + conversion.offset == pytest.approx(0.0, abs=1e-9)
    assert 212 * conversion.factor + conversion.offset == pytest.approx(100.0)


def test_molar_spellings_are_ucum_only() -> None:
    # UCUM has no molar unit: M is the mega prefix. v0.1 migrated to umol/L rather than carry an
    # alias, so the old spellings must not resolve at all.
    assert factor("umol/L", "mol/L") == pytest.approx(1e-6)
    assert factor("nmol/L", "umol/L") == pytest.approx(1e-3)
    for retired in ("uM", "nM", "mM"):
        with pytest.raises(UnitError):
            parse_unit(retired, TABLE)


@pytest.mark.parametrize(("source", "target"), [("mg", "s"), ("kg", "s"), ("mg/L", "umol/L")])
def test_different_dimensions_do_not_convert(source: str, target: str) -> None:
    assert convert_unit(source, target, TABLE) is None


@pytest.mark.parametrize(("source", "target"), [
    ("[PFU]/mL", "[TCID_50]/mL"),
    ("[IU]/mL", "{BAU}/mL"),
    ("Cel/min", "K/min"),
    ("fmol/(cell.h)", "fmol/h"),
])
def test_undecidable_pairs_raise_rather_than_pass(source: str, target: str) -> None:
    with pytest.raises(UnitError):
        convert_unit(source, target, TABLE)


def test_a_multi_digit_number_is_one_factor() -> None:
    assert parse_unit("86400", TABLE).factor == pytest.approx(86400.0)


def test_dimension_alone_cannot_tell_frequency_from_radioactivity() -> None:
    # A known limit of dimensional analysis, and the reason the standard also records quantity kinds.
    assert factor("Hz", "Bq") == pytest.approx(1.0)

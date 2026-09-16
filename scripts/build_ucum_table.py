"""Flatten the pinned UCUM definitions into one table both implementations can read.

UCUM defines each unit in terms of another unit expression. Resolving that chain needs a parser,
and writing one parser per language invites the two from drifting apart. So the chain is resolved
once, here, at build time: every unit code becomes a factor, a dimension vector, and, for the
affine units, an offset. At runtime each language only has to parse an *expression* over this flat
table, which is a much smaller job.

    python3 scripts/build_ucum_table.py

Input is the vendored UCUM 2.2 `ucum-essence.xml`; the generated table records
its SHA-256. Output is `source/vendor/ucum/ucum-table.json`.
"""
from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "source" / "vendor" / "ucum"
SOURCE_XML = VENDOR / "ucum-essence.xml"
OUT = VENDOR / "ucum-table.json"
NS = "{http://unitsofmeasure.org/ucum-essence}"

# Base dimensions in a fixed order, so a dimension is comparable as a plain list.
DIMENSIONS = ["L", "T", "M", "A", "C", "Q", "F"]

# No aliases. UCUM has no molar unit -- 'M' is the mega prefix, so 'uM' parses as micro-mega --
# and v0.1 has not been released, so the declarations use UCUM spellings (umol/L, nmol/L) directly
# rather than carrying informal aliases.
ALIASES: dict[str, str] = {}


class Unresolved(Exception):
    """A unit whose definition this resolver cannot express as factor, dimension and offset."""


def zero() -> list[int]:
    return [0] * len(DIMENSIONS)


def multiply(left: list[int], right: list[int], power: int = 1) -> list[int]:
    return [a + b * power for a, b in zip(left, right)]


TOKEN = re.compile(r"""
    (?P<open>\()
  | (?P<close>\))
  | (?P<operator>[./])
  | (?P<annotation>\{[^}]*\})
  | (?P<number>\d+)(?=$|[./(){}]|\{)
  | (?P<code>\[[^\]]*\]|[^./(){}\s]+?)(?P<exponent>[+-]?\d+)?(?=$|[./(){}]|\{)
""", re.VERBOSE)


def parse(expression: str, lookup) -> tuple[float, list[int]]:
    """Parse a UCUM expression into a factor and a dimension vector."""
    position = 0
    text = expression.strip()

    def component() -> tuple[float, list[int]]:
        nonlocal position
        match = TOKEN.match(text, position)
        if not match:
            raise Unresolved(f"cannot parse {expression!r} at {position}")
        position = match.end()
        if match.group("open"):
            factor, dimension = sequence()
            closing = TOKEN.match(text, position)
            if not closing or not closing.group("close"):
                raise Unresolved(f"unbalanced parentheses in {expression!r}")
            position = closing.end()
            return factor, dimension
        if match.group("annotation"):
            return 1.0, zero()
        if match.group("operator") or match.group("close"):
            raise Unresolved(f"unexpected operator in {expression!r}")
        if match.group("number"):
            # A bare integer is a factor in its own right: 86400 is not 8 to the 6400th.
            return float(match.group("number")), zero()
        code, exponent = match.group("code"), int(match.group("exponent") or 1)
        factor, dimension = lookup(code)
        trailing = TOKEN.match(text, position)
        if trailing and trailing.group("annotation"):
            # An annotation binds to the unit before it and carries no semantics.
            position = trailing.end()
        return factor ** exponent, [value * exponent for value in dimension]

    def sequence() -> tuple[float, list[int]]:
        nonlocal position
        factor, dimension = 1.0, zero()
        leading = TOKEN.match(text, position)
        if leading and leading.group("operator") == "/":
            position = leading.end()
            right_factor, right_dimension = component()
            factor, dimension = 1.0 / right_factor, multiply(zero(), right_dimension, -1)
        else:
            factor, dimension = component()
        while position < len(text):
            match = TOKEN.match(text, position)
            if not match or not match.group("operator"):
                break
            position = match.end()
            operator = match.group("operator")
            right_factor, right_dimension = component()
            if operator == ".":
                factor *= right_factor
                dimension = multiply(dimension, right_dimension)
            else:
                factor /= right_factor
                dimension = multiply(dimension, right_dimension, -1)
        return factor, dimension

    factor, dimension = sequence()
    if position != len(text):
        raise Unresolved(f"trailing input in {expression!r}")
    return factor, dimension


def build() -> dict:
    raw = SOURCE_XML.read_bytes()
    root = ET.fromstring(raw)
    prefixes = {node.attrib["Code"]: float(node.find(NS + "value").attrib["value"])
                for node in root.findall(NS + "prefix")}
    units: dict[str, dict] = {}
    for index, node in enumerate(root.findall(NS + "base-unit")):
        dimension = zero()
        dimension[DIMENSIONS.index(node.attrib["dim"])] = 1
        units[node.attrib["Code"]] = {"factor": 1.0, "dim": dimension, "metric": True,
                                      "property": node.findtext(NS + "property", "").strip()}
    definitions = {node.attrib["Code"]: node for node in root.findall(NS + "unit")}
    resolving: set[str] = set()
    unresolved: dict[str, str] = {}

    def lookup(code: str) -> tuple[float, list[int]]:
        entry = resolve(code)
        if entry is None:
            raise Unresolved(f"unknown unit code {code!r}")
        return entry["factor"], entry["dim"]

    def lookup_with_prefix(code: str) -> tuple[float, list[int]]:
        try:
            return lookup(code)
        except Unresolved:
            for length in (2, 1):
                prefix, rest = code[:length], code[length:]
                if prefix in prefixes and rest:
                    entry = resolve(rest)
                    if entry is not None and entry.get("metric"):
                        return prefixes[prefix] * entry["factor"], entry["dim"]
            raise

    def resolve(code: str) -> dict | None:
        if code in units:
            return units[code]
        node = definitions.get(code)
        if node is None or code in unresolved:
            return None
        if code in resolving:
            raise Unresolved(f"circular definition for {code!r}")
        resolving.add(code)
        try:
            value = node.find(NS + "value")
            function = value.find(NS + "function") if value is not None else None
            if function is not None:
                name = function.attrib.get("name")
                if name not in {"Cel", "degF", "degRe"}:
                    raise Unresolved(f"{code!r} uses the non-affine function {name!r}")
                scale, dimension = parse(function.attrib["Unit"], lookup_with_prefix)
                factor = float(function.attrib.get("value", "1")) * scale
                offset = {"Cel": 273.15, "degF": 459.67 * factor, "degRe": 273.15}[name]
                entry = {"factor": factor, "dim": dimension, "offset": offset,
                         "metric": node.attrib.get("isMetric") == "yes"}
            else:
                factor, dimension = parse(value.attrib["Unit"], lookup_with_prefix)
                entry = {"factor": float(value.attrib.get("value", "1")) * factor, "dim": dimension,
                         "metric": node.attrib.get("isMetric") == "yes"}
            if node.attrib.get("isArbitrary") == "yes":
                entry["arbitrary"] = True
            entry["property"] = node.findtext(NS + "property", "").strip()
            units[code] = entry
            return entry
        except Unresolved as error:
            unresolved[code] = str(error)
            return None
        finally:
            resolving.discard(code)

    for code in definitions:
        resolve(code)

    for alias, target in ALIASES.items():
        if alias in units:
            raise SystemExit(f"alias {alias!r} collides with a real UCUM code")

    return {
        "schema_version": "0.1",
        "generated_by": "scripts/build_ucum_table.py",
        "ucum": {"version": root.attrib.get("version"), "revision_date": root.attrib.get("revision-date"),
                 "sha256": "sha256:" + hashlib.sha256(raw).hexdigest()},
        "note": ("Every unit resolved to a factor over the UCUM base units, a dimension vector in the order "
                 "given by 'dimensions', and for affine units an offset such that base_value = factor * value + offset. "
                 "Units flagged arbitrary are not commensurable with anything else, per UCUM section 24, so they convert "
                 "only to themselves. Units UCUM defines through logarithmic or other non-affine functions are listed in "
                 "'unresolved' and must never be converted silently."),
        "dimensions": DIMENSIONS,
        "prefixes": prefixes,
        "aliases": ALIASES,
        "alias_note": "Informal spellings that UCUM does not define are unsupported; use the UCUM spelling.",
        "units": {code: units[code] for code in sorted(units)},
        "unresolved": dict(sorted(unresolved.items())),
    }


def main() -> None:
    table = build()
    OUT.write_text(json.dumps(table, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(f"UCUM {table['ucum']['version']} ({table['ucum']['revision_date']})")
    print(f"  prefixes  {len(table['prefixes'])}")
    print(f"  units     {len(table['units'])} resolved, {len(table['unresolved'])} not representable")
    print(f"  arbitrary {sum(1 for u in table['units'].values() if u.get('arbitrary'))}")
    print(f"  affine    {sorted(c for c, u in table['units'].items() if 'offset' in u)}")
    if table["unresolved"]:
        print("  unresolved:", ", ".join(sorted(table["unresolved"])[:12]))
    print(f"written: {OUT}")


if __name__ == "__main__":
    main()

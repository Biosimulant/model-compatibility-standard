"""Unit expressions: parse a UCUM code, and say whether two units convert.

The heavy lifting happened at build time: scripts/build_ucum_table.py resolved every UCUM unit to
a factor, a dimension vector and, where the unit is affine, an offset. This module parses an
expression over that table and answers one question: can a value in unit A be expressed in unit B,
and by what factor?

Three answers are distinct, and the standard needs all three:

- convertible, with a factor and possibly an offset;
- not convertible, because the dimensions differ (a known contradiction);
- not decidable, because a unit is unparseable, arbitrary or logarithmic (UNKNOWN, never a pass).

See decision D1.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

TOKEN = re.compile(r"""
    (?P<open>\()
  | (?P<close>\))
  | (?P<operator>[./])
  | (?P<annotation>\{[^}]*\})
  | (?P<number>\d+)(?=$|[./(){}]|\{)
  | (?P<code>\[[^\]]*\]|[^./(){}\s]+?)(?P<exponent>[+-]?\d+)?(?=$|[./(){}]|\{)
""", re.VERBOSE)


class UnitError(ValueError):
    """The expression cannot be interpreted, so no comparison may be inferred from it."""


@dataclass(frozen=True)
class Quantity:
    """A parsed unit: a factor over the base units, plus its dimension."""

    factor: float
    dimension: tuple[int, ...]
    offset: float = 0.0
    arbitrary_codes: frozenset[str] = frozenset()
    codes: frozenset[str] = frozenset()

    @property
    def dimensionless(self) -> bool:
        return not any(self.dimension)


@dataclass(frozen=True)
class Conversion:
    """How to get from one unit to another. value_in_target = value * factor + offset."""

    factor: float
    offset: float
    affine: bool
    lossless: bool = True


def parse_unit(expression: str, table: dict[str, Any]) -> Quantity:
    """Parse a UCUM expression against a flattened table. Raises UnitError when it cannot."""
    if not isinstance(expression, str) or not expression.strip():
        raise UnitError("empty unit")
    text = table.get("aliases", {}).get(expression.strip(), expression.strip())
    units, prefixes = table["units"], table["prefixes"]
    width = len(table["dimensions"])
    position = 0
    arbitrary: set[str] = set()
    used: set[str] = set()
    offsets: list[float] = []
    components = 0
    operators = 0

    def resolve(code: str) -> tuple[float, list[int]]:
        entry = units.get(code)
        if entry is None:
            for length in (2, 1):
                prefix, rest = code[:length], code[length:]
                candidate = units.get(rest)
                if prefix in prefixes and candidate is not None and candidate.get("metric"):
                    entry = {**candidate, "factor": prefixes[prefix] * candidate["factor"]}
                    break
        if entry is None:
            raise UnitError(f"unknown unit code {code!r}")
        used.add(code)
        if entry.get("arbitrary"):
            arbitrary.add(code)
        if entry.get("offset"):
            offsets.append(entry["offset"])
        return entry["factor"], entry["dim"]

    def component() -> tuple[float, list[int]]:
        nonlocal position, components
        match = TOKEN.match(text, position)
        if not match:
            raise UnitError(f"cannot parse {expression!r}")
        position = match.end()
        if match.group("open"):
            factor, dimension = sequence()
            closing = TOKEN.match(text, position)
            if not closing or not closing.group("close"):
                raise UnitError(f"unbalanced parentheses in {expression!r}")
            position = closing.end()
            return factor, dimension
        if match.group("annotation"):
            return 1.0, [0] * width
        if match.group("operator") or match.group("close"):
            raise UnitError(f"unexpected operator in {expression!r}")
        if match.group("number"):
            # A bare integer is a factor in its own right: 86400 is not 8 to the 6400th.
            return float(match.group("number")), [0] * width
        code, exponent = match.group("code"), int(match.group("exponent") or 1)
        components += 1
        factor, dimension = resolve(code)
        trailing = TOKEN.match(text, position)
        if trailing and trailing.group("annotation"):
            # An annotation binds to the unit before it and carries no semantics: g{DW} is grams.
            position = trailing.end()
        return factor ** exponent, [value * exponent for value in dimension]

    def sequence() -> tuple[float, list[int]]:
        nonlocal position, operators
        leading = TOKEN.match(text, position)
        if leading and leading.group("operator") == "/":
            position = leading.end()
            operators += 1
            right_factor, right_dimension = component()
            factor, dimension = 1.0 / right_factor, [-value for value in right_dimension]
        else:
            factor, dimension = component()
        while position < len(text):
            match = TOKEN.match(text, position)
            if not match or not match.group("operator"):
                break
            position = match.end()
            operators += 1
            operator = match.group("operator")
            right_factor, right_dimension = component()
            if operator == ".":
                factor *= right_factor
                dimension = [a + b for a, b in zip(dimension, right_dimension)]
            else:
                factor /= right_factor
                dimension = [a - b for a, b in zip(dimension, right_dimension)]
        return factor, dimension

    factor, dimension = sequence()
    if position != len(text):
        raise UnitError(f"trailing input in {expression!r}")
    if offsets and (len(offsets) > 1 or operators or components != 1):
        # Celsius converts on its own. A degree Celsius per minute does not: the offset has no
        # meaning once the unit is combined with anything else.
        raise UnitError(f"{expression!r} combines an affine unit with other units")
    return Quantity(factor, tuple(dimension), offsets[0] if offsets else 0.0, frozenset(arbitrary), frozenset(used))


def convert_unit(source: str, target: str, table: dict[str, Any]) -> Conversion | None:
    """Return how to convert source into target, or None when the dimensions differ.

    Raises UnitError when the question cannot be decided: an unparseable code, or an arbitrary
    unit such as [IU] or [PFU], which UCUM defines as commensurable with nothing but itself.
    """
    if source == target:
        return Conversion(1.0, 0.0, affine=False)
    left, right = parse_unit(source, table), parse_unit(target, table)
    if left.arbitrary_codes or right.arbitrary_codes:
        if left.arbitrary_codes != right.arbitrary_codes:
            raise UnitError("arbitrary units are commensurable only with themselves")
    if left.dimension != right.dimension:
        return None
    factor = left.factor / right.factor
    offset = (left.offset - right.offset) / right.factor
    return Conversion(factor, offset, affine=offset != 0.0)

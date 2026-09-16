// Unit expressions: parse a UCUM code, and say whether two units convert.
//
// The resolution of UCUM's definition chains happened at build time
// (scripts/build_ucum_table.py). This module parses an expression over that flat table and
// answers one question: can a value in unit A be expressed in unit B, and by what factor?
//
// Three answers are distinct, and the standard needs all three: convertible with a factor and
// possibly an offset; not convertible because the dimensions differ; and not decidable, because a
// unit is unparseable, arbitrary or logarithmic. The last must never resolve as a pass.
//
// Mirrors python/src/biosimulant_model_compatibility_standard/units.py.

export interface UnitTable {
  dimensions: string[];
  prefixes: Record<string, number>;
  aliases?: Record<string, string>;
  units: Record<string, { factor: number; dim: number[]; metric?: boolean; offset?: number; arbitrary?: boolean }>;
}

export interface Quantity {
  factor: number;
  dimension: number[];
  offset: number;
  arbitraryCodes: string[];
  codes: string[];
}

export interface Conversion {
  factor: number;
  offset: number;
  affine: boolean;
  lossless: boolean;
}

export class UnitError extends Error {}

const TOKEN = /(\()|(\))|([./])|(\{[^}]*\})|(\d+)(?=$|[./(){}]|\{)|(\[[^\]]*\]|[^./(){}\s]+?)([+-]?\d+)?(?=$|[./(){}]|\{)/y;

export function parseUnit(expression: string, table: UnitTable): Quantity {
  if (typeof expression !== "string" || !expression.trim()) throw new UnitError("empty unit");
  const text = table.aliases?.[expression.trim()] ?? expression.trim();
  const width = table.dimensions.length;
  const arbitrary = new Set<string>();
  const used = new Set<string>();
  const offsets: number[] = [];
  let position = 0;
  let components = 0;
  let operators = 0;

  const zero = () => new Array(width).fill(0);

  const next = () => {
    TOKEN.lastIndex = position;
    const match = TOKEN.exec(text);
    if (!match) throw new UnitError(`cannot parse ${expression}`);
    position = TOKEN.lastIndex;
    return match;
  };

  const peek = () => {
    TOKEN.lastIndex = position;
    return TOKEN.exec(text);
  };

  const resolve = (code: string): [number, number[]] => {
    let entry = table.units[code];
    if (!entry) {
      for (const length of [2, 1]) {
        const prefix = code.slice(0, length), rest = code.slice(length);
        const candidate = table.units[rest];
        if (table.prefixes[prefix] !== undefined && candidate?.metric) {
          entry = { ...candidate, factor: table.prefixes[prefix] * candidate.factor };
          break;
        }
      }
    }
    if (!entry) throw new UnitError(`unknown unit code ${code}`);
    used.add(code);
    if (entry.arbitrary) arbitrary.add(code);
    if (entry.offset) offsets.push(entry.offset);
    return [entry.factor, entry.dim];
  };

  const component = (): [number, number[]] => {
    const match = next();
    if (match[1]) {
      const inner = sequence();
      const closing = next();
      if (!closing[2]) throw new UnitError(`unbalanced parentheses in ${expression}`);
      return inner;
    }
    if (match[4]) return [1, zero()];
    if (match[3] || match[2]) throw new UnitError(`unexpected operator in ${expression}`);
    // A bare integer is a factor in its own right: 86400 is not 8 to the 6400th.
    if (match[5]) return [Number(match[5]), zero()];
    const code = match[6], exponent = match[7] ? Number.parseInt(match[7], 10) : 1;
    components += 1;
    const [factor, dimension] = resolve(code);
    const trailing = peek();
    // An annotation binds to the unit before it and carries no semantics: g{DW} is grams.
    if (trailing && trailing[4]) position = TOKEN.lastIndex;
    return [factor ** exponent, dimension.map((value) => value * exponent)];
  };

  const sequence = (): [number, number[]] => {
    let factor: number, dimension: number[];
    const leading = peek();
    if (leading && leading[3] === "/") {
      position = TOKEN.lastIndex;
      operators += 1;
      const [rightFactor, rightDimension] = component();
      factor = 1 / rightFactor;
      dimension = rightDimension.map((value) => -value);
    } else {
      [factor, dimension] = component();
    }
    while (position < text.length) {
      const match = peek();
      if (!match || !match[3]) break;
      position = TOKEN.lastIndex;
      operators += 1;
      const operator = match[3];
      const [rightFactor, rightDimension] = component();
      if (operator === ".") {
        factor *= rightFactor;
        dimension = dimension.map((value, index) => value + rightDimension[index]);
      } else {
        factor /= rightFactor;
        dimension = dimension.map((value, index) => value - rightDimension[index]);
      }
    }
    return [factor, dimension];
  };

  const [factor, dimension] = sequence();
  if (position !== text.length) throw new UnitError(`trailing input in ${expression}`);
  if (offsets.length && (offsets.length > 1 || operators || components !== 1)) {
    // Celsius converts on its own. A degree Celsius per minute does not: the offset has no
    // meaning once the unit is combined with anything else.
    throw new UnitError(`${expression} combines an affine unit with other units`);
  }
  return { factor, dimension, offset: offsets[0] ?? 0, arbitraryCodes: [...arbitrary].sort(), codes: [...used].sort() };
}

/**
 * How to convert source into target, or null when the dimensions differ.
 * Throws UnitError when the question cannot be decided.
 */
export function convertUnit(source: string, target: string, table: UnitTable): Conversion | null {
  if (source === target) return { factor: 1, offset: 0, affine: false, lossless: true };
  const left = parseUnit(source, table), right = parseUnit(target, table);
  if (left.arbitraryCodes.length || right.arbitraryCodes.length) {
    if (JSON.stringify(left.arbitraryCodes) !== JSON.stringify(right.arbitraryCodes)) {
      throw new UnitError("arbitrary units are commensurable only with themselves");
    }
  }
  if (JSON.stringify(left.dimension) !== JSON.stringify(right.dimension)) return null;
  const factor = left.factor / right.factor;
  const offset = (left.offset - right.offset) / right.factor;
  return { factor, offset, affine: offset !== 0, lossless: true };
}

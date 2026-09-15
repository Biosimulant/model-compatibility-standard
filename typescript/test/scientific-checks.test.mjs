// Scientific checks for v0.1: known defects and the guards that remediation must keep.
//
// The cases live in scientific-checks/v0.1/cases.json and are shared with
// python/tests/test_scientific_checks.py. A defect case asserts the scientifically correct
// outcome. By default it passes only while the defect still reproduces, so a fix fails the
// suite until the case becomes a guard. Set BMCS_SCIENTIFIC_STRICT=1 to run defects as
// ordinary failing tests.
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

import { compareContracts, normalizeContract, validateContract } from "../dist/index.js";
import { parseUnit, UnitError } from "../dist/units.js";

const ROOT = fileURLToPath(new URL("../../", import.meta.url));
const SUITE = JSON.parse(readFileSync(join(ROOT, "scientific-checks", "v0.1", "cases.json"), "utf8"));
const FIXTURES = join(ROOT, "spec", "v0.1", "fixtures", "profiles");
const UNITS = JSON.parse(readFileSync(join(ROOT, "spec", "v0.1", "rules", "units.json"), "utf8"));

/** The dimension the standard's own UCUM table gives this unit, or null when it cannot say. */
function dimensionOf(unit) {
  if (typeof unit !== "string") return null;
  try {
    return JSON.stringify(parseUnit(unit, UNITS).dimension);
  } catch (error) {
    if (error instanceof UnitError) return null;
    throw error;
  }
}
const STRICT = process.env.BMCS_SCIENTIFIC_STRICT === "1";
const NOT_A_MATCH = "is not scientifically acceptable here";

const ref = (profile) => `${SUITE.profile_ref_prefix}${profile}${SUITE.profile_ref_suffix}`;
const fixtureCases = (file) => Object.fromEntries(JSON.parse(readFileSync(file, "utf8")).cases.map((entry) => [entry.name, entry]));

function merge(base, patch) {
  for (const [key, value] of Object.entries(patch)) {
    if (value && typeof value === "object" && !Array.isArray(value) && base[key] && typeof base[key] === "object" && !Array.isArray(base[key])) {
      merge(base[key], value);
    } else {
      base[key] = structuredClone(value);
    }
  }
}

function contractFor(entry, side) {
  const contract = structuredClone(fixtureCases(join(FIXTURES, `${entry.profile}.json`)).positive.contract);
  merge(contract, entry[`${side}_patch`] ?? {});
  for (const path of entry[`${side}_remove`] ?? []) {
    const parts = path.split(".");
    const leaf = parts.pop();
    let node = contract;
    for (const part of parts) node = node?.[part] ?? {};
    delete node[leaf];
  }
  return contract;
}

function offenders(invariant) {
  const found = [];
  for (const domain of readdirSync(FIXTURES).sort()) {
    for (const file of readdirSync(join(FIXTURES, domain)).filter((name) => name.endsWith(".json")).sort()) {
      const profile = `${domain}/${file.slice(0, -5)}`;
      const cases = fixtureCases(join(FIXTURES, domain, file));
      const measurement = cases.positive.contract.measurement ?? {};
      if (invariant === "conversion-within-dimension") {
        const entry = cases["comparison-lossless-unit-conversion"];
        if (entry) {
          const units = [entry.source.measurement.unit, entry.target.measurement.unit, measurement.unit];
          const dims = new Set(units.map(dimensionOf));
          if (dims.has(null) || dims.size !== 1) found.push(`${profile}: ${units[0]} -> ${units[1]} for a quantity in ${measurement.unit}`);
        }
      } else if (invariant === "contradiction-cross-dimension") {
        const entry = cases["comparison-incompatible-measurement-unit"];
        if (entry) {
          const [left, right] = [entry.source.measurement.unit, entry.target.measurement.unit];
          if (dimensionOf(left) === null || dimensionOf(right) === null || dimensionOf(left) === dimensionOf(right)) {
            found.push(`${profile}: ${left} vs ${right} asserted INCOMPATIBLE`);
          }
        }
      } else if (invariant === "probability-scale-dimensionless") {
        if (measurement.scale === "probability" && dimensionOf(measurement.unit) !== JSON.stringify([0, 0, 0, 0, 0, 0, 0])) {
          found.push(`${profile}: probability scale with unit ${measurement.unit}`);
        }
      } else {
        throw new Error(`unknown invariant ${invariant}`);
      }
    }
  }
  return found;
}

function violations(entry) {
  const expect = entry.expect;
  const found = [];
  if (entry.check === "compare") {
    const refs = [ref(entry.profile)];
    let source = contractFor(entry, "source");
    let target = contractFor(entry, "target");
    if (entry.normalize) { source = normalizeContract(source); target = normalizeContract(target); }
    const report = compareContracts(source, target, { sourceProfileRefs: refs, targetProfileRefs: refs });
    if ("status" in expect && report.status !== expect.status) found.push(`status ${report.status}, expected ${expect.status}`);
    if ((expect.status_not_in ?? []).includes(report.status)) found.push(`status ${report.status} ${NOT_A_MATCH}`);
    if ("policy_decision_not" in expect && report.policy_decision === expect.policy_decision_not) found.push(`policy decision ${report.policy_decision} ${NOT_A_MATCH}`);
  } else if (entry.check === "validate") {
    const errors = validateContract(contractFor(entry, "source"), [ref(entry.profile)]).filter((item) => item.severity === "error");
    if (expect.error_findings === "at-least-one" && errors.length === 0) found.push("contract validated with no error finding");
  } else if (entry.check === "fixture-invariant") {
    const list = offenders(entry.invariant);
    if (list.length) found.push(`${list.length} offending profiles, e.g. ${list.slice(0, 3).join("; ")}`);
  } else {
    throw new Error(`unknown check ${entry.check}`);
  }
  return found;
}

for (const entry of SUITE.cases.filter((item) => item.kind === "defect")) {
  test(`${entry.id} [known defect] ${entry.title}`, () => {
    const found = violations(entry);
    if (STRICT) {
      assert.deepEqual(found, [], `${entry.id}: ${found.join("; ")}`);
    } else {
      assert.ok(found.length > 0, `${entry.id} no longer reproduces. Confirm the fix is scientifically right, then change its kind to "guard".`);
    }
  });
}

for (const entry of SUITE.cases.filter((item) => item.kind === "guard")) {
  test(`${entry.id} [guard] ${entry.title}`, () => {
    const found = violations(entry);
    assert.deepEqual(found, [], `${entry.id}: ${found.join("; ")}`);
  });
}

test("scientific case file is well formed", () => {
  const ids = SUITE.cases.map((entry) => entry.id);
  assert.equal(new Set(ids).size, ids.length);
  for (const entry of SUITE.cases) {
    assert.ok(["defect", "guard"].includes(entry.kind), entry.id);
    assert.ok(["compare", "validate", "fixture-invariant"].includes(entry.check), entry.id);
    for (const key of ["title", "why", "conditions", "decision", "expect", "report_finding"]) assert.ok(entry[key], `${entry.id}: ${key}`);
    if (entry.kind === "defect") assert.ok(entry.observed_at_review, entry.id);
  }
});

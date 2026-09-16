// Scientific guards shared by the Python and TypeScript implementations.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

import { compareContracts, normalizeContract, resolveContracts, validateContract } from "../dist/index.js";

const ROOT = fileURLToPath(new URL("../../", import.meta.url));
const SUITE = JSON.parse(readFileSync(join(ROOT, "scientific-checks", "v0.1", "cases.json"), "utf8"));
const FIXTURES = join(ROOT, "spec", "v0.1", "fixtures", "profiles");
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
    // A governance outcome is reported separately from the technical findings.
    if ("policy_finding_reason_code" in expect && !(report.policy_findings ?? []).some((item) => item.reason_code === expect.policy_finding_reason_code)) found.push(`no policy finding ${expect.policy_finding_reason_code}`);
  } else if (entry.check === "validate") {
    const errors = validateContract(contractFor(entry, "source"), [ref(entry.profile)]).filter((item) => item.severity === "error");
    if (expect.error_findings === "at-least-one" && errors.length === 0) found.push("contract validated with no error finding");
  } else if (entry.check === "resolve") {
    // The lossy and inference statuses are produced by the resolution layer, not by comparison, so a
    // case that exercises an approval path has to plan a capability chain.
    const source = contractFor(entry, "source");
    const target = contractFor(entry, "target");
    const capabilities = (entry.capabilities ?? []).map((capability) => {
      const filled = structuredClone(capability);
      for (const side of ["source", "target"]) {
        if (filled[side] === "$source") filled[side] = structuredClone(source);
        else if (filled[side] === "$target") filled[side] = structuredClone(target);
      }
      return filled;
    });
    const result = resolveContracts(source, target, capabilities);
    const plan = result.plan ?? {};
    // The chain's own status, not the terminal comparison: reports[] is EXACT whenever the last
    // adapter lands exactly on the target, which would make an approval-path case vacuous.
    const status = plan.technical_status;
    const decision = (plan.policy ?? {}).decision;
    if ("resolution" in expect && result.resolution !== expect.resolution) found.push(`resolution ${result.resolution}, expected ${expect.resolution}`);
    if ("plan_status" in expect && status !== expect.plan_status) found.push(`plan status ${status}, expected ${expect.plan_status}`);
    if ("policy_decision" in expect && decision !== expect.policy_decision) found.push(`policy decision ${decision}, expected ${expect.policy_decision}`);
    if ("policy_decision_not" in expect && decision === expect.policy_decision_not) found.push(`policy decision ${decision} ${NOT_A_MATCH}`);
  } else {
    throw new Error(`unknown check ${entry.check}`);
  }
  return found;
}

for (const entry of SUITE.cases) {
  test(`${entry.id} [guard] ${entry.title}`, () => {
    const found = violations(entry);
    assert.deepEqual(found, [], `${entry.id}: ${found.join("; ")}`);
  });
}

test("scientific case file is well formed", () => {
  const ids = SUITE.cases.map((entry) => entry.id);
  assert.equal(new Set(ids).size, ids.length);
  for (const entry of SUITE.cases) {
    assert.equal(entry.kind, "guard", entry.id);
    assert.ok(["compare", "validate", "resolve"].includes(entry.check), entry.id);
    for (const key of ["title", "why", "conditions", "decision", "expect", "report_finding"]) assert.ok(entry[key], `${entry.id}: ${key}`);
    assert.ok(readFileSync(join(FIXTURES, `${entry.profile}.json`)), entry.id);
  }
});

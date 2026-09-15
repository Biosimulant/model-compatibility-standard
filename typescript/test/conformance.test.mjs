import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

import { Bundle, canonicalJson, compareContracts, digest, getBundle, parseYaml, validateContract, validateManifest, validateObject } from "../dist/index.js";

test("bundle exposes all catalogue entries", () => {
  const bundle = getBundle();
  assert.equal(bundle.catalogue.counts.profiles, 650);
  assert.equal(bundle.catalogue.counts.item_definitions, 266);
  assert.equal(bundle.catalogue.counts.item_packs, 30);
});

test("positive, negative and unknown fixtures pass for every profile", () => {
  const bundle = getBundle();
  for (const summary of bundle.catalogue.profiles) {
    const fixture = bundle.readJson(`fixtures/profiles/${summary.domain}/${summary.name}.json`);
    const [positive, negative, unknown] = fixture.cases;
    assert.deepEqual(validateContract(positive.contract, [fixture.profile_ref]), [], fixture.profile_ref);
    assert.ok(validateContract(negative.contract, [fixture.profile_ref]).some((item) => item.reason_code === negative.reason_code), fixture.profile_ref);
    assert.equal(compareContracts(unknown.source, unknown.target, { targetProfileRefs: [fixture.profile_ref] }).status, unknown.status, fixture.profile_ref);
  }
});

test("example manifests with and without a compatibility block validate", () => {
  const bundle = getBundle();
  const legacy = parseYaml(readFileSync(join(bundle.root, "examples/legacy-model.yaml"), "utf8"));
  const optedIn = parseYaml(readFileSync(join(bundle.root, "examples/compatible-model.yaml"), "utf8"));
  assert.deepEqual(validateManifest(legacy), []);
  assert.deepEqual(validateManifest(optedIn), []);
});

test("digest ignores key order and comparisons return the expected statuses", () => {
  assert.equal(digest({ b: 2, a: 1 }), digest({ a: 1, b: 2 }));
  const contract = { semantic: { concept: "concentration" } };
  const exact = compareContracts(contract, contract);
  assert.equal(exact.status, "EXACT");
  assert.deepEqual(validateObject(exact, "compatibility-report.schema.json"), []);
  assert.equal(compareContracts(null, contract).status, "UNKNOWN");
  assert.equal(compareContracts({ measurement: { unit: "nM" } }, { measurement: { unit: "uM" } }).status, "LOSSLESS_CONVERSION_AVAILABLE");
  assert.equal(compareContracts({ biological_context: { compartment: "extracellular" } }, { biological_context: { compartment: "intracellular" } }).status, "INCOMPATIBLE");
});

test("committed cross-language golden vectors match", () => {
  const bundle = getBundle();
  const canonical = bundle.readJson("fixtures/golden/canonicalization.json");
  for (const entry of canonical.cases) {
    assert.equal(canonicalJson(entry.input), entry.canonical, entry.name);
    assert.equal(digest(entry.input), entry.sha256, entry.name);
  }
  const comparisons = bundle.readJson("fixtures/golden/comparison-statuses.json");
  for (const entry of comparisons.cases) {
    assert.equal(compareContracts(entry.source, entry.target).status, entry.status, entry.name);
  }
});

test("reordered axis labels are a lossless conversion", () => {
  class PermutationBundle extends Bundle {
    profile() {
      return { comparison_rules: [{ source: "/contract/dimensions/axes", target: "/contract/dimensions/axes", operator: "labels-permutation", missing: "unknown", reason_code: "BMCS_VALUE_MISMATCH" }] };
    }
  }
  const report = compareContracts({ dimensions: { axes: ["gene", "sample"] } }, { dimensions: { axes: ["sample", "gene"] } }, { targetProfileRefs: ["test"], bundle: new PermutationBundle() });
  assert.equal(report.status, "LOSSLESS_CONVERSION_AVAILABLE");
  assert.equal(report.policy_decision, "ALLOW");
});

test("Python and TypeScript use the same unknown-profile reason code", () => {
  const reasonCodes = getBundle().readJson("rules/reason-codes.json").reason_codes;
  const findings = validateContract({}, ["https://biosimulant.com/standards/model-compatibility/profiles/core/missing/v0.1"]);
  assert.deepEqual(findings.map((item) => item.reason_code), ["BMCS_PROFILE_UNRESOLVED"]);
  assert.ok(findings.every((item) => item.reason_code in reasonCodes));
});

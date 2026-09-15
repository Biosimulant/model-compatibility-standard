import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

import { Bundle, buildCompatibilityLock, canonicalJson, compareContracts, digest, getBundle, normalizeContract, parseYaml, resolveContracts, validateContract, validateManifest, validateObject } from "../dist/index.js";

test("bundle exposes all catalogue entries", () => {
  const bundle = getBundle();
  assert.equal(bundle.catalogue.counts.profiles, 650);
  assert.equal(bundle.catalogue.counts.item_definitions, 266);
  assert.equal(bundle.catalogue.counts.item_packs, 30);
  bundle.verifyIntegrity();
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

test("accepted profile contracts add details but cannot change common invariants", () => {
  const bundle = getBundle();
  const manifest = parseYaml(readFileSync(join(bundle.root, "examples/compatible-model.yaml"), "utf8"));
  const port = manifest.io.inputs[0];
  port.accepted_profiles = [{ contract: { measurement: { unit: "count" } } }];
  assert.deepEqual(validateManifest(manifest), []);
  port.accepted_profiles[0].contract = { biological_context: { species: "NCBITaxon:10090" } };
  assert.ok(validateManifest(manifest).some((item) => item.reason_code === "BMCS_REFINEMENT_WEAKENS_CONTRACT"));
});

test("normalization and compatibility locks are deterministic", () => {
  const bundle = getBundle();
  const manifest = parseYaml(readFileSync(join(bundle.root, "examples/compatible-model.yaml"), "utf8"));
  manifest.io.inputs[0].contract.semantic.qualifiers = ["z", "a"];
  const first = buildCompatibilityLock(manifest);
  manifest.io.inputs[0].contract.semantic.qualifiers = ["a", "z"];
  const second = buildCompatibilityLock(manifest);
  assert.deepEqual(first, second);
  assert.deepEqual(normalizeContract({ semantic: { qualifiers: ["z", "a"] } }), { semantic: { qualifiers: ["a", "z"] } });
  assert.deepEqual(validateObject(first, "compatibility-lock.schema.json"), []);
});

class RuleBundle extends Bundle {
  constructor(rule) {
    super();
    this.rule = rule;
  }
  profile() {
    return { comparison_rules: [this.rule] };
  }
}

function ruleReport(operator, source, target, { parameters, ontology = [], mappings = [] } = {}) {
  const rule = { source: "/contract/value/current", target: "/contract/value/current", operator, missing: "unknown", reason_code: "BMCS_VALUE_MISMATCH", ...(parameters ? { parameters } : {}) };
  return compareContracts({ value: { current: source } }, { value: { current: target } }, { targetProfileRefs: ["test"], bundle: new RuleBundle(rule), snapshots: { ontology, mappings } });
}

test("the complete scalar, collection, range, pattern and dimension operator set works", () => {
  assert.equal(ruleReport("in", "a", ["a", "b"]).status, "DIRECT_COMPATIBLE");
  assert.equal(ruleReport("not-in", "c", ["a", "b"]).status, "DIRECT_COMPATIBLE");
  assert.equal(ruleReport("range", { minimum: 2, maximum: 4 }, { minimum: 1, maximum: 5 }).status, "DIRECT_COMPATIBLE");
  assert.equal(ruleReport("pattern", "ENSG0001", "ignored", { parameters: { pattern: "ENSG[0-9]+" } }).status, "DIRECT_COMPATIBLE");
  assert.equal(ruleReport("same-dimension", "nM", "uM").status, "DIRECT_COMPATIBLE");
});

test("ontology and mapping operators require exact digest-pinned snapshots", () => {
  const ontologyUnsigned = { ref: "https://biosimulant.com/snapshots/test-ontology/v1", equivalences: [["TERM:A", "TERM:A_ALIAS"]], subsumptions: [{ parent: "TERM:PARENT", child: "TERM:CHILD" }] };
  const ontology = { ...ontologyUnsigned, sha256: digest(ontologyUnsigned) };
  const ontologyParameters = { snapshot_ref: ontology.ref, snapshot_sha256: ontology.sha256 };
  assert.equal(ruleReport("term-equivalent", "TERM:A_ALIAS", "TERM:A", { parameters: ontologyParameters, ontology: [ontology] }).status, "DIRECT_COMPATIBLE");
  assert.equal(ruleReport("term-subsumes", "TERM:CHILD", "TERM:PARENT", { parameters: ontologyParameters, ontology: [ontology] }).status, "DIRECT_COMPATIBLE");
  assert.equal(ruleReport("term-subsumes", "TERM:CHILD", "TERM:PARENT", { parameters: ontologyParameters }).status, "UNKNOWN");

  const mappingUnsigned = { ref: "https://biosimulant.com/snapshots/test-mapping/v1", mappings: [{ source: "A", target: "1" }, { source: "B", target: "2" }] };
  const mapping = { ...mappingUnsigned, sha256: digest(mappingUnsigned) };
  const mappingParameters = { snapshot_ref: mapping.ref, snapshot_sha256: mapping.sha256 };
  assert.equal(ruleReport("mapping-total", ["A", "B"], ["1", "2"], { parameters: mappingParameters, mappings: [mapping] }).status, "DIRECT_COMPATIBLE");
  assert.equal(ruleReport("mapping-bijective", ["A", "B"], ["1", "2"], { parameters: mappingParameters, mappings: [mapping] }).status, "DIRECT_COMPATIBLE");
});

function adapter(ref, source, target, loss = "none") {
  return { schema_version: "0.1", ref, sha256: digest({ release: ref }), source, target, state: "reviewed", transformation_class: "unit", information_loss: loss, loss_score: loss === "none" ? 0 : 1, execution_cost: 1, release: { version: "1.0.0" } };
}

test("TypeScript resolver exposes adapters, ambiguity, and revocation", () => {
  const source = { semantic: { concept: "a" } };
  const target = { semantic: { concept: "b" } };
  const first = adapter("https://biosimulant.com/adapters/a/1.0.0", source, target);
  const resolved = resolveContracts(source, target, [first]);
  assert.equal(resolved.resolution, "RESOLVED");
  assert.deepEqual(resolved.plan.nodes.map((node) => node.kind), ["contract", "adapter", "contract"]);
  const ambiguous = resolveContracts(source, target, [first, adapter("https://biosimulant.com/adapters/b/1.0.0", source, target)]);
  assert.equal(ambiguous.resolution, "AMBIGUOUS");
  first.state = "revoked";
  assert.equal(resolveContracts(source, target, [first]).resolution, "UNRESOLVED");
});

test("resource limits fail closed with a stable reason code", () => {
  const real = getBundle();
  const limited = new Bundle(real.root, { ...real.limits, maxDepth: 2 });
  assert.deepEqual(validateContract({ semantic: { ontology_terms: [{ uri: "x" }] } }, [], limited).map((item) => item.reason_code), ["BMCS_RESOURCE_LIMIT_EXCEEDED"]);
});

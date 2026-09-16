import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

import { Bundle, buildCompatibilityLock, canonicalJson, compareContracts, digest, getBundle, normalizeContract, parseYaml, resolveContracts, validateContract, validateManifest, validateObject } from "../dist/index.js";

test("bundle exposes all catalogue entries", () => {
  const bundle = getBundle();
  assert.equal(bundle.catalogue.counts.profiles, bundle.catalogue.profiles.length);
  assert.ok(bundle.catalogue.counts.fields > 0);
  assert.ok(bundle.catalogue.profiles.length > 0);
  assert.equal(new Set(bundle.catalogue.profiles.map((profile) => profile.id)).size, bundle.catalogue.profiles.length);
  for (const summary of bundle.catalogue.profiles) {
    assert.deepEqual(validateObject(bundle.profile(summary.ref), "profile-definition.schema.json"), []);
  }
  bundle.verifyIntegrity();
});

test("the full external-review fixture set passes for every profile", () => {
  const bundle = getBundle();
  for (const summary of bundle.catalogue.profiles) {
    const fixture = bundle.readJson(`fixtures/profiles/${summary.domain}/${summary.name}.json`);
    const cases = Object.fromEntries(fixture.cases.map((entry) => [entry.name, entry]));
    const profile = bundle.profile(fixture.profile_ref);
    const required = profile.requirements.filter((item) => item.level === "required");
    // Count the lossless cases rather than test that any exist: a profile can now carry both a unit
    // conversion and a representation re-encoding.
    const lossless = Object.keys(cases).filter((name) => name.startsWith("comparison-lossless")).length;
    // A requirement addressing every member of an array is validated, not compared: no pointer means
    // "each element", so it carries the two negative fixtures and none of the three comparison ones
    //.
    const memberRequired = required.filter((item) => String(item.path).includes("[]")).length;
    const expectedCount = 2 + (5 * (required.length - memberRequired)) + (2 * memberRequired) + lossless;
    assert.equal(fixture.cases.length, expectedCount, fixture.profile_ref);
    const positive = cases.positive;
    assert.deepEqual(validateContract(positive.contract, [fixture.profile_ref]), [], fixture.profile_ref);
    for (const entry of fixture.cases) {
      if (entry.name.startsWith("negative-")) {
        assert.ok(validateContract(entry.contract, [fixture.profile_ref]).some((item) => item.reason_code === entry.reason_code), `${fixture.profile_ref}: ${entry.name}`);
      } else if (entry.name.startsWith("comparison-")) {
        const report = compareContracts(entry.source, entry.target, { targetProfileRefs: [fixture.profile_ref] });
        assert.equal(report.status, entry.status, `${fixture.profile_ref}: ${entry.name}`);
        if (entry.reason_code) assert.ok(report.findings.some((item) => item.reason_code === entry.reason_code), `${fixture.profile_ref}: ${entry.name}`);
      }
    }
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
  assert.equal(compareContracts({ measurement: { unit: "nmol/L" } }, { measurement: { unit: "umol/L" } }).status, "LOSSLESS_CONVERSION_AVAILABLE");
  // uM is not a UCUM code: M is the mega prefix. An unreadable unit is undecidable, never a match.
  assert.equal(compareContracts({ measurement: { unit: "nM" } }, { measurement: { unit: "uM" } }).status, "UNKNOWN");
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
  port.accepted_profiles = [{ contract: { measurement: { unit: "1" } } }];
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
  // same-dimension is convertibility, decided against the published UCUM table. It used to read a
  // four-row table whose rows were nM/uM, so it answered for those two spellings and nothing else.
  assert.equal(ruleReport("same-dimension", "g", "kg").status, "DIRECT_COMPATIBLE");
  assert.equal(ruleReport("same-dimension", "Cel", "K").status, "DIRECT_COMPATIBLE");
  assert.equal(ruleReport("same-dimension", "g", "s").status, "INCOMPATIBLE");
  // nM and uM are not UCUM codes: M is the mega prefix. Unreadable is undecidable, never a match.
  assert.equal(ruleReport("same-dimension", "nM", "uM").status, "UNKNOWN");
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
  // A pinned mapping that is total and bijective loses nothing, but translating identifiers is still
  // a conversion rather than a direct match.
  assert.equal(ruleReport("mapping-total", ["A", "B"], ["1", "2"], { parameters: mappingParameters, mappings: [mapping] }).status, "LOSSLESS_CONVERSION_AVAILABLE");
  assert.equal(ruleReport("mapping-bijective", ["A", "B"], ["1", "2"], { parameters: mappingParameters, mappings: [mapping] }).status, "LOSSLESS_CONVERSION_AVAILABLE");

  // A mapping that is total but merges two identifiers onto one is not reversible, so it needs
  // approval rather than passing as a lossless translation.
  const mergingUnsigned = { ref: "https://biosimulant.com/snapshots/test-merge/v1", mappings: [{ source: "A", target: "1" }, { source: "B", target: "1" }] };
  const merging = { ...mergingUnsigned, sha256: digest(mergingUnsigned) };
  const mergeParameters = { snapshot_ref: merging.ref, snapshot_sha256: merging.sha256 };
  const merged = ruleReport("mapping-total", ["A", "B"], ["1"], { parameters: mergeParameters, mappings: [merging] });
  assert.equal(merged.status, "LOSSY_CONVERSION_REQUIRES_APPROVAL");
  assert.equal(merged.policy_decision, "APPROVAL_REQUIRED");
  // The same merging snapshot cannot satisfy a bijective requirement at all.
  assert.equal(ruleReport("mapping-bijective", ["A", "B"], ["1"], { parameters: mergeParameters, mappings: [merging] }).status, "INCOMPATIBLE");
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

test("a profile's published transformation policy reaches the plan", () => {
  // Every profile publishes transformation_policy and nothing read it: the only policy consulted was
  // the one a caller passed in by hand, so a profile's declared approval paths had no effect on any
  // plan.
  const ref = "https://biosimulant.com/standards/model-compatibility/profiles/proteome/protein-sequence/v0.1";
  const source = { measurement: { unit: "Hz", scale: "nominal" }, profile_refs: [ref] };
  const target = { measurement: { unit: "Hz", scale: "ordinal" }, profile_refs: [ref] };
  const capability = adapter("https://biosimulant.com/adapters/rate-to-ordinal-band/1.0.0", source, target, "lossy");
  capability.transformation_class = "aggregation";
  const result = resolveContracts(source, target, [capability]);
  assert.equal(result.resolution, "RESOLVED");
  assert.equal(result.plan.technical_status, "LOSSY_CONVERSION_REQUIRES_APPROVAL");
  // Read from the profile, translated out of the published allow/approval/block vocabulary.
  assert.equal(result.plan.policy.lossy, "APPROVAL_REQUIRED");
  assert.equal(result.plan.policy.lossless, "ALLOW");
  assert.equal(result.plan.policy.decision, "APPROVAL_REQUIRED");
  assert.deepEqual(validateObject(result.plan, "resolution-plan.schema.json"), []);
});

test("TypeScript resolver checks preconditions and pins snapshots", () => {
  const source = { semantic: { concept: "source" } };
  const target = { semantic: { concept: "target" } };
  const capability = adapter("https://biosimulant.com/adapters/precondition/1.0.0", source, target);
  capability.preconditions = [{
    source: "/contract/semantic/concept",
    target: "/contract/semantic/concept",
    operator: "equal",
    missing: "incompatible",
    reason_code: "BMCS_PRECONDITION_FAILED",
  }];
  assert.equal(resolveContracts(source, target, [capability]).resolution, "RESOLVED");
  capability.preconditions[0].operator = "not-equal";
  assert.equal(resolveContracts(source, target, [capability]).resolution, "UNRESOLVED");

  const contract = { semantic: { concept: "concentration" } };
  const unsigned = { ref: "https://biosimulant.com/snapshots/test-ontology/1.0.0", equivalences: [] };
  const snapshot = { ...unsigned, sha256: digest(unsigned) };
  const resolved = resolveContracts(contract, contract, [], { snapshots: { ontology: [snapshot] } });
  assert.deepEqual(resolved.report.snapshots.ontology, [{ ref: snapshot.ref, sha256: snapshot.sha256 }]);
  assert.ok(resolved.plan.immutable_references.some((item) => item.kind === "ontology_snapshot" && item.ref === snapshot.ref && item.sha256 === snapshot.sha256));
});

test("resource limits fail closed with a stable reason code", () => {
  const real = getBundle();
  const limited = new Bundle(real.root, { ...real.limits, maxDepth: 2 });
  assert.deepEqual(validateContract({ semantic: { ontology_terms: [{ uri: "x" }] } }, [], limited).map((item) => item.reason_code), ["BMCS_RESOURCE_LIMIT_EXCEEDED"]);
});


test("the term registry is published and version independent", () => {
  const bundle = getBundle();
  const registry = bundle.readJson("catalogue/terms.json");
  const expected = bundle.catalogue.counts.profiles;
  assert.equal(registry.count, expected);
  assert.equal(registry.terms.length, expected);
  const ids = registry.terms.map((term) => term.id);
  assert.equal(new Set(ids).size, expected);
  // A term must outlive the profile version that minted it, or a v0.2 profile would report every
  // v0.1 port as incompatible even where the meaning is unchanged.
  assert.deepEqual(ids.filter((id) => id.includes("/v0.")), []);
  assert.ok(registry.terms.every((term) => term.label && term.definition));
  // External terms remain empty until a reviewer decides whether an exact maintained term exists.
  assert.ok(registry.terms.every((term) => Array.isArray(term.external_terms) && term.external_terms.length === 0));
});


test("a namespace release change is a mapping, not a contradiction", () => {
  // Two releases of one namespace are not a contradiction: identifiers are retired and
  // merged between releases, so what matters is what the transition did.
  const snapshot = (transitions) => {
    const unsigned = { ref: "https://biosimulant.com/snapshots/ensembl-releases/v1", namespace: "ensembl", transitions };
    const signed = { ...unsigned, sha256: digest(unsigned) };
    return [signed, { snapshot_ref: signed.ref, snapshot_sha256: signed.sha256 }];
  };
  const [clean, cleanParameters] = snapshot([{ from: "110", to: "114", identifiers_retired: 0, identifiers_merged: 0 }]);
  const [lossy, lossyParameters] = snapshot([{ from: "110", to: "114", identifiers_retired: 12, identifiers_merged: 3 }]);

  // A transition that retired and merged nothing preserves every identifier.
  assert.equal(ruleReport("namespace-version-compatible", "110", "114", { parameters: cleanParameters, mappings: [clean] }).status, "LOSSLESS_CONVERSION_AVAILABLE");
  // One that retired or merged identifiers is a real loss and needs approval.
  const approval = ruleReport("namespace-version-compatible", "110", "114", { parameters: lossyParameters, mappings: [lossy] });
  assert.equal(approval.status, "LOSSY_CONVERSION_REQUIRES_APPROVAL");
  assert.equal(approval.policy_decision, "APPROVAL_REQUIRED");
  // Without a pinned snapshot nobody can say, which is undecidable rather than a mismatch.
  assert.equal(ruleReport("namespace-version-compatible", "110", "114").status, "UNKNOWN");
  // A snapshot that says nothing about this pair of releases decides nothing either.
  assert.equal(ruleReport("namespace-version-compatible", "110", "999", { parameters: cleanParameters, mappings: [clean] }).status, "UNKNOWN");
});

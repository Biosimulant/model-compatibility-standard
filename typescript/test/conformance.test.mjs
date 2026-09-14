import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

import { compareContracts, digest, getBundle, parseYaml, validateContract, validateManifest } from "../dist/index.js";

test("bundle exposes all catalogue entries", () => {
  const bundle = getBundle();
  assert.equal(bundle.catalogue.counts.profiles, 650);
  assert.equal(bundle.catalogue.counts.item_definitions, 266);
  assert.equal(bundle.catalogue.counts.item_packs, 30);
});

test("every profile positive and negative fixture is executable", () => {
  const bundle = getBundle();
  for (const summary of bundle.catalogue.profiles) {
    const fixture = bundle.readJson(`fixtures/profiles/${summary.domain}/${summary.name}.json`);
    const [positive, negative] = fixture.cases;
    assert.deepEqual(validateContract(positive.contract, [fixture.profile_ref]), [], fixture.profile_ref);
    assert.ok(validateContract(negative.contract, [fixture.profile_ref]).some((item) => item.reason_code === negative.reason_code), fixture.profile_ref);
  }
});

test("legacy and opted-in examples validate", () => {
  const bundle = getBundle();
  const legacy = parseYaml(readFileSync(join(bundle.root, "examples/legacy-model.yaml"), "utf8"));
  const optedIn = parseYaml(readFileSync(join(bundle.root, "examples/compatible-model.yaml"), "utf8"));
  assert.deepEqual(validateManifest(legacy), []);
  assert.deepEqual(validateManifest(optedIn), []);
});

test("digests and primary statuses are deterministic", () => {
  assert.equal(digest({ b: 2, a: 1 }), digest({ a: 1, b: 2 }));
  const contract = { semantic: { concept: "concentration" } };
  assert.equal(compareContracts(contract, contract).status, "EXACT");
  assert.equal(compareContracts(null, contract).status, "UNKNOWN");
  assert.equal(compareContracts({ measurement: { unit: "nM" } }, { measurement: { unit: "uM" } }).status, "LOSSLESS_CONVERSION_AVAILABLE");
  assert.equal(compareContracts({ biological_context: { compartment: "extracellular" } }, { biological_context: { compartment: "intracellular" } }).status, "INCOMPATIBLE");
});

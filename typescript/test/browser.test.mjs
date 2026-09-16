import assert from "node:assert/strict";
import test from "node:test";

import {
  getBrowserBundle,
  parseYaml,
  validateContract,
  validateManifest,
} from "../dist/browser.js";

test("browser entry has all active profiles and validates without Node file APIs", () => {
  const bundle = getBrowserBundle();
  assert.equal(bundle.catalogue.counts.profiles, bundle.catalogue.profiles.length);
  assert.deepEqual(validateManifest(parseYaml('schema_version: "2.0"\n')), []);

  const summary = bundle.catalogue.profiles[0];
  const profile = bundle.profile(summary.ref);
  const contract = {};
  assert.ok(profile.requirements.length > 0);
  assert.ok(validateContract(contract, [summary.ref]).length > 0);
});

test("browser entry checks imported profile digests", () => {
  const summary = getBrowserBundle().catalogue.profiles[0];
  const manifest = {
    schema_version: "2.0",
    compatibility: {
      standard: "https://biosimulant.com/standards/model-compatibility/v0.1",
      profiles: [{ ref: summary.ref, sha256: `sha256:${"0".repeat(64)}` }],
    },
    io: { inputs: [], outputs: [] },
  };
  assert.ok(
    validateManifest(manifest).some(
      (finding) => finding.reason_code === "BMCS_DIGEST_MISMATCH",
    ),
  );
});

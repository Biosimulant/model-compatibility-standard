#!/usr/bin/env node

import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import {
  buildCompatibilityLock,
  compareContracts,
  digest,
  getBundle,
  normalizeContract,
  resolveContracts,
} from "../typescript/dist/index.js";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const bundle = getBundle();
const profile = bundle.catalogue.profiles.find((item) => item.ref.endsWith("/proteome/protein-sequence/v0.1"));
assert.ok(profile);

const manifest = {
  schema_version: "2.0",
  compatibility: { standard: "https://biosimulant.com/standards/model-compatibility/v0.1", profiles: [{ ref: profile.ref, sha256: profile.sha256 }] },
  io: {
    inputs: [{ name: "protein_sequence", signal_type: "record", contract: { profile_refs: [profile.ref], semantic: { concept: "https://biosimulant.com/standards/model-compatibility/terms/proteome/protein-sequence", subject: "protein", qualifiers: ["z", "a"] }, representation: { kind: "record", alphabet: "amino-acid", encoding: "single-letter" }, identifiers: { namespace: "uniprot", namespace_version: "release-pinned" }, biological_context: { species: "NCBITaxon:9606" } } }],
    outputs: [],
  },
};
const source = { semantic: { concept: "a" } };
const target = { semantic: { concept: "b" } };
const capability = { schema_version: "0.1", ref: "https://biosimulant.com/adapters/a/1.0.0", sha256: digest({ release: "https://biosimulant.com/adapters/a/1.0.0" }), source, target, state: "reviewed", transformation_class: "unit", information_loss: "none", loss_score: 0, execution_cost: 1, release: { version: "1.0.0" } };
const input = { manifest, source, target, capability };
const javascript = {
  normalized: normalizeContract(manifest.io.inputs[0].contract),
  lock: buildCompatibilityLock(manifest),
  report: compareContracts(source, target),
  resolution: resolveContracts(source, target, [capability]),
};

const venvPython = join(root, ".venv", "bin", "python");
const python = process.env.PYTHON ?? (existsSync(venvPython) ? venvPython : "python3");
const program = String.raw`
import json, sys
from biosimulant_model_compatibility_standard import build_compatibility_lock, compare_contracts, normalize_contract, resolve_contracts
value = json.load(sys.stdin)
result = {
    "normalized": normalize_contract(value["manifest"]["io"]["inputs"][0]["contract"]),
    "lock": build_compatibility_lock(value["manifest"]),
    "report": compare_contracts(value["source"], value["target"]),
    "resolution": resolve_contracts(value["source"], value["target"], [value["capability"]]),
}
json.dump(result, sys.stdout, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
`;
const result = spawnSync(python, ["-c", program], {
  cwd: root,
  input: JSON.stringify(input),
  encoding: "utf8",
  env: { ...process.env, PYTHONPATH: join(root, "python", "src") },
});
if (result.status !== 0) throw new Error(`Python conformance process failed:\n${result.stderr}`);
const pythonOutput = JSON.parse(result.stdout);
assert.deepEqual(javascript, pythonOutput);
console.log("Python and TypeScript normalization, locks, reports, plans, and digests match.");

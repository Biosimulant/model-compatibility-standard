import { createHash } from "node:crypto";
import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import Ajv2020Import, { type ErrorObject, type ValidateFunction } from "ajv/dist/2020.js";
import addFormatsImport from "ajv-formats";
import canonicalizeImport from "canonicalize";
import YAML from "yaml";

export const STANDARD = "https://biosimulant.com/standards/model-compatibility/v0.1";
const PROFILE_PREFIX = "https://biosimulant.com/standards/model-compatibility/profiles/";

export type JsonValue = null | boolean | number | string | JsonValue[] | { [key: string]: JsonValue };
export type JsonObject = { [key: string]: JsonValue };
export type TechnicalStatus =
  | "EXACT"
  | "DIRECT_COMPATIBLE"
  | "LOSSLESS_CONVERSION_AVAILABLE"
  | "LOSSY_CONVERSION_REQUIRES_APPROVAL"
  | "INFERENCE_MODEL_REQUIRED"
  | "CONDITIONAL"
  | "INCOMPATIBLE"
  | "UNKNOWN";

export interface ValidationFinding {
  reason_code: string;
  message: string;
  path: string;
  severity: "error" | "warning" | "info";
}

export interface CompatibilityFinding {
  dimension: string;
  state: TechnicalStatus;
  severity: "error" | "warning" | "info";
  reason_code: string;
  explanation: string;
  evidence?: JsonValue;
}

export interface CompatibilityReport {
  schema_version: "0.1";
  standard: typeof STANDARD;
  bundle_sha256: string;
  source: JsonObject;
  target: JsonObject;
  status: TechnicalStatus;
  policy_decision: "ALLOW" | "APPROVAL_REQUIRED" | "BLOCK";
  findings: CompatibilityFinding[];
  digest: string;
}

function moduleSpecRoot(): string {
  return join(dirname(fileURLToPath(import.meta.url)), "..", "..", "spec", "v0.1");
}

export class Bundle {
  readonly root: string;
  private readonly cache = new Map<string, JsonObject>();

  constructor(root = moduleSpecRoot()) {
    this.root = root;
  }

  readJson(relativePath: string): JsonObject {
    const cached = this.cache.get(relativePath);
    if (cached) return cached;
    const value = JSON.parse(readFileSync(join(this.root, relativePath), "utf8")) as JsonObject;
    this.cache.set(relativePath, value);
    return value;
  }

  get manifest(): JsonObject {
    return this.readJson("bundle.manifest.json");
  }

  get catalogue(): JsonObject {
    return this.readJson("catalogue/catalogue.json");
  }

  profile(ref: string): JsonObject {
    if (!ref.startsWith(PROFILE_PREFIX)) throw new Error(`Unknown profile reference: ${ref}`);
    const relative = ref.slice(PROFILE_PREFIX.length);
    return this.readJson(`profiles/${relative}.json`);
  }

  profileSummary(ref: string): JsonObject | undefined {
    return (this.catalogue.profiles as JsonObject[]).find((entry) => entry.ref === ref);
  }

  schemaFiles(): string[] {
    return readdirSync(join(this.root, "schemas")).filter((name) => name.endsWith(".json")).sort();
  }

  unitConversions(): JsonObject[] {
    return this.readJson("rules/unit-conversions.json").conversions as JsonObject[];
  }
}

let sharedBundle: Bundle | undefined;
export function getBundle(): Bundle {
  sharedBundle ??= new Bundle();
  return sharedBundle;
}

const canonicalizeFunction = ((canonicalizeImport as unknown as { default?: typeof canonicalizeImport }).default ?? canonicalizeImport) as unknown as (value: unknown) => string | undefined;

export function canonicalJson(value: unknown): string {
  const encoded = canonicalizeFunction(value);
  if (encoded === undefined) throw new TypeError("Value is not valid canonical JSON");
  return encoded;
}

export function digest(value: unknown): string {
  return `sha256:${createHash("sha256").update(canonicalJson(value), "utf8").digest("hex")}`;
}

type AjvInstance = {
  addSchema(schema: JsonObject): void;
  getSchema(identifier: string): ValidateFunction | undefined;
  compile(schema: JsonObject): ValidateFunction;
};
const Ajv2020 = ((Ajv2020Import as unknown as { default?: unknown }).default ?? Ajv2020Import) as unknown as new (options: Record<string, unknown>) => AjvInstance;
const addFormats = ((addFormatsImport as unknown as { default?: unknown }).default ?? addFormatsImport) as unknown as (ajv: AjvInstance) => void;

function validator(bundle: Bundle): AjvInstance {
  const ajv = new Ajv2020({ allErrors: true, strict: false });
  addFormats(ajv);
  for (const name of bundle.schemaFiles()) ajv.addSchema(bundle.readJson(`schemas/${name}`));
  return ajv;
}

function schemaFindings(errors: ErrorObject[] | null | undefined): ValidationFinding[] {
  return (errors ?? []).map((error) => ({
    reason_code: "BMCS_SCHEMA_INVALID",
    message: error.message ?? error.keyword,
    path: error.instancePath,
    severity: "error",
  }));
}

function getDotted(document: JsonObject, path: string): JsonValue | undefined {
  let current: JsonValue = document;
  for (const segment of path.split(".")) {
    if (typeof current !== "object" || current === null || Array.isArray(current) || !(segment in current)) return undefined;
    current = current[segment];
  }
  return current;
}

function getPointer(document: JsonObject, pointer: string): JsonValue | undefined {
  let current: JsonValue = document;
  for (const raw of pointer.slice(1).split("/")) {
    const segment = raw.replaceAll("~1", "/").replaceAll("~0", "~");
    if (typeof current !== "object" || current === null || Array.isArray(current) || !(segment in current)) return undefined;
    current = current[segment];
  }
  return current;
}

export function validateContract(contract: JsonObject, profileRefs: string[] = [], bundle = getBundle()): ValidationFinding[] {
  const ajv = validator(bundle);
  const schema = bundle.readJson("schemas/port-contract.schema.json");
  const check = ajv.getSchema(schema.$id as string)!;
  check(contract);
  const findings = schemaFindings(check.errors);
  for (const ref of profileRefs) {
    let profile: JsonObject;
    try {
      profile = bundle.profile(ref);
    } catch {
      findings.push({ reason_code: "BMCS_PROFILE_UNRESOLVED", message: `Unknown profile: ${ref}`, path: "/profile_refs", severity: "error" });
      continue;
    }
    for (const requirement of profile.requirements as JsonObject[]) {
      if (requirement.level !== "required") continue;
      const path = requirement.path as string;
      const value = getDotted(contract, path);
      if (value === undefined || value === null) {
        findings.push({ reason_code: "BMCS_REQUIRED_MISSING", message: `${ref} requires ${path}`, path: `/${path.replaceAll(".", "/")}`, severity: "error" });
        continue;
      }
      const checkRequirement = ajv.compile(requirement.schema as JsonObject);
      if (!checkRequirement(value)) {
        findings.push({ reason_code: "BMCS_PROFILE_VALUE_INVALID", message: `${path} does not satisfy the profile requirement`, path: `/${path.replaceAll(".", "/")}`, severity: "error" });
      }
    }
  }
  return findings;
}

export function validateObject(instance: JsonValue, schemaName: string, bundle = getBundle()): ValidationFinding[] {
  const ajv = validator(bundle);
  const normalizedName = schemaName.endsWith(".json") ? schemaName : `${schemaName}.json`;
  if (!bundle.schemaFiles().includes(normalizedName)) throw new Error(`Unknown standard schema: ${schemaName}`);
  const schema = bundle.readJson(`schemas/${normalizedName}`);
  const check = ajv.getSchema(schema.$id as string)!;
  check(instance);
  return schemaFindings(check.errors);
}

export function validateManifest(manifest: JsonObject, bundle = getBundle()): ValidationFinding[] {
  if (!("compatibility" in manifest)) return [];
  const ajv = validator(bundle);
  const schema = bundle.readJson("schemas/manifest-extension.schema.json");
  const check = ajv.getSchema(schema.$id as string)!;
  check(manifest);
  const findings = schemaFindings(check.errors);
  const compatibility = manifest.compatibility as JsonObject;
  const imports = new Map<string, JsonObject>();
  for (const item of (compatibility.profiles ?? []) as JsonObject[]) imports.set(item.ref as string, item);
  for (const [ref, imported] of imports) {
    const expected = bundle.profileSummary(ref);
    if (!expected) findings.push({ reason_code: "BMCS_PROFILE_UNRESOLVED", message: `Unknown profile: ${ref}`, path: "/compatibility/profiles", severity: "error" });
    else if (imported.sha256 !== expected.sha256) findings.push({ reason_code: "BMCS_DIGEST_MISMATCH", message: `Profile digest does not match ${ref}`, path: "/compatibility/profiles", severity: "error" });
  }
  const io = manifest.io as JsonObject;
  for (const direction of ["inputs", "outputs"]) {
    for (const [index, rawPort] of ((io?.[direction] ?? []) as JsonObject[]).entries()) {
      const contract = rawPort.contract as JsonObject | undefined;
      if (!contract) continue;
      const refs = (contract.profile_refs ?? []) as string[];
      for (const ref of refs) if (!imports.has(ref)) findings.push({ reason_code: "BMCS_PROFILE_NOT_IMPORTED", message: `Port profile is not imported: ${ref}`, path: `/io/${direction}/${index}/contract/profile_refs`, severity: "error" });
      findings.push(...validateContract(contract, refs, bundle));
    }
  }
  return findings;
}

function finding(dimension: string, state: TechnicalStatus, reason: string, explanation: string, evidence?: JsonValue): CompatibilityFinding {
  return { dimension, state, severity: state === "INCOMPATIBLE" ? "error" : "info", reason_code: reason, explanation, ...(evidence === undefined ? {} : { evidence }) };
}

function rulesFor(refs: string[], bundle: Bundle): JsonObject[] {
  const result: JsonObject[] = [];
  const seen = new Set<string>();
  for (const ref of [...new Set(refs)].sort()) {
    for (const rule of bundle.profile(ref).comparison_rules as JsonObject[]) {
      const key = `${rule.source}\0${rule.target}\0${rule.operator}`;
      if (!seen.has(key)) { seen.add(key); result.push(rule); }
    }
  }
  return result;
}

function compareValue(operator: string, source: JsonValue, target: JsonValue, bundle: Bundle): [boolean, string | undefined] {
  if (["equal", "digest-equal", "term-equivalent", "same-dimension", "labels-equal"].includes(operator)) return [canonicalJson(source) === canonicalJson(target), undefined];
  if (operator === "not-equal") return [canonicalJson(source) !== canonicalJson(target), undefined];
  if (operator === "subset" || operator === "superset") {
    const left = new Set(source as JsonValue[]), right = new Set(target as JsonValue[]);
    return [operator === "subset" ? [...left].every((value) => right.has(value)) : [...right].every((value) => left.has(value)), undefined];
  }
  if (operator === "labels-permutation") return [(source as JsonValue[]).length === (target as JsonValue[]).length && [...source as JsonValue[]].sort().every((value, index) => canonicalJson(value) === canonicalJson([...target as JsonValue[]].sort()[index])), "none"];
  if (operator === "unit-convertible") {
    if (source === target) return [true, undefined];
    const conversion = bundle.unitConversions().find((entry) => entry.from === source && entry.to === target);
    return [conversion !== undefined, conversion?.loss as string | undefined];
  }
  if (operator === "context-compatible") return [source === target || target === "any" || target === "unspecified" || target === null, undefined];
  return [false, "unsupported"];
}

export function compareContracts(source: JsonObject | null, target: JsonObject | null, options: { sourceProfileRefs?: string[]; targetProfileRefs?: string[]; bundle?: Bundle } = {}): CompatibilityReport {
  const bundle = options.bundle ?? getBundle();
  let status: TechnicalStatus;
  let findings: CompatibilityFinding[];
  if (source === null || target === null) {
    status = "UNKNOWN";
    findings = [finding("contract", "UNKNOWN", "BMCS_CONTRACT_NOT_DECLARED", "Compatibility metadata is not declared on both ports.")];
  } else if (digest(source) === digest(target)) {
    status = "EXACT";
    findings = [finding("contract", "EXACT", "BMCS_EXACT_CONTRACT", "Canonical contract digests are identical.")];
  } else {
    const refs = options.targetProfileRefs?.length ? options.targetProfileRefs : options.sourceProfileRefs ?? [];
    let rules = refs.length ? rulesFor(refs, bundle) : [];
    if (!rules.length) {
      for (const [family, members] of Object.entries(target)) {
        if (["profile_refs", "extensions"].includes(family) || typeof members !== "object" || members === null || Array.isArray(members)) continue;
        for (const name of Object.keys(members)) rules.push({ source: `/contract/${family}/${name}`, target: `/contract/${family}/${name}`, operator: family === "measurement" && ["unit", "units"].includes(name) ? "unit-convertible" : "equal", missing: "unknown", reason_code: "BMCS_VALUE_MISMATCH" });
      }
    }
    findings = [];
    let unknown = false, incompatible = false, conversion: string | undefined;
    for (const rule of rules) {
      const left = getPointer({ contract: source }, rule.source as string), right = getPointer({ contract: target }, rule.target as string);
      const dimension = (rule.target as string).split("/")[2] ?? "contract";
      if (left === undefined || right === undefined) {
        if (rule.missing === "ignore") continue;
        unknown = true;
        findings.push(finding(dimension, "UNKNOWN", "BMCS_REQUIRED_EVIDENCE_MISSING", `Evidence is missing for ${rule.target}.`));
        continue;
      }
      const [compatible, transformation] = compareValue(rule.operator as string, left, right, bundle);
      if (transformation === "unsupported") { unknown = true; findings.push(finding(dimension, "UNKNOWN", "BMCS_OPERATOR_REQUIRES_SNAPSHOT", `${rule.operator} requires pinned external evidence.`)); }
      else if (compatible) { conversion = transformation ?? conversion; findings.push(finding(dimension, "DIRECT_COMPATIBLE", "BMCS_RULE_SATISFIED", `${rule.operator} comparison passed.`)); }
      else { incompatible = true; findings.push(finding(dimension, "INCOMPATIBLE", rule.reason_code as string, `${rule.operator} comparison failed.`, { source: left, target: right })); }
    }
    status = incompatible ? "INCOMPATIBLE" : unknown ? "UNKNOWN" : conversion === "none" ? "LOSSLESS_CONVERSION_AVAILABLE" : conversion ? "LOSSY_CONVERSION_REQUIRES_APPROVAL" : "DIRECT_COMPATIBLE";
  }
  const partial = {
    schema_version: "0.1" as const,
    standard: STANDARD as typeof STANDARD,
    bundle_sha256: bundle.manifest.bundle_sha256 as string,
    source: { contract_digest: source ? digest(source) : null, profile_refs: [...new Set(options.sourceProfileRefs ?? [])].sort() },
    target: { contract_digest: target ? digest(target) : null, profile_refs: [...new Set(options.targetProfileRefs ?? [])].sort() },
    status,
    policy_decision: (["LOSSY_CONVERSION_REQUIRES_APPROVAL", "INFERENCE_MODEL_REQUIRED", "CONDITIONAL"].includes(status) ? "APPROVAL_REQUIRED" : ["INCOMPATIBLE", "UNKNOWN"].includes(status) ? "BLOCK" : "ALLOW") as "ALLOW" | "APPROVAL_REQUIRED" | "BLOCK",
    findings,
  };
  return { ...partial, digest: digest(partial) };
}

export function parseYaml(text: string): JsonObject {
  return YAML.parse(text) as JsonObject;
}

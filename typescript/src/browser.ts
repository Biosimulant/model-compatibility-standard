import Ajv2020Import, {
  type ErrorObject,
  type ValidateFunction,
} from "ajv/dist/2020.js";
import addFormatsImport from "ajv-formats";
import YAML from "yaml";

import browserData from "./browser-data.json" with { type: "json" };

export const STANDARD = "https://biosimulant.com/standards/model-compatibility/v0.1";
const PROFILE_PREFIX = `${STANDARD.replace("/v0.1", "")}/profiles/`;

export type JsonValue =
  | null
  | boolean
  | number
  | string
  | JsonValue[]
  | { [key: string]: JsonValue };
export type JsonObject = { [key: string]: JsonValue };

export interface ValidationFinding {
  reason_code: string;
  message: string;
  path: string;
  severity: "error" | "warning" | "info";
}

export interface ResourceLimits {
  maxDocumentBytes: number;
  maxDepth: number;
  maxNodes: number;
  maxStringBytes: number;
  maxArrayItems: number;
  maxObjectProperties: number;
  maxProfileRefs: number;
  maxRules: number;
}

export const DEFAULT_RESOURCE_LIMITS: Readonly<ResourceLimits> = {
  maxDocumentBytes: 4 * 1024 * 1024,
  maxDepth: 64,
  maxNodes: 200_000,
  maxStringBytes: 1024 * 1024,
  maxArrayItems: 100_000,
  maxObjectProperties: 100_000,
  maxProfileRefs: 100,
  maxRules: 10_000,
};

export class ResourceLimitError extends Error {}

function utf8Bytes(value: string): number {
  return new TextEncoder().encode(value).byteLength;
}

export function ensureJsonLimits(
  value: unknown,
  limits: ResourceLimits = DEFAULT_RESOURCE_LIMITS,
): void {
  let nodes = 0;
  const active = new Set<object>();
  const stack: Array<{ value: unknown; depth: number; leaving?: boolean }> = [
    { value, depth: 0 },
  ];
  while (stack.length) {
    const item = stack.pop()!;
    const current = item.value;
    if (item.leaving) {
      active.delete(current as object);
      continue;
    }
    nodes += 1;
    if (nodes > limits.maxNodes) {
      throw new ResourceLimitError(
        `Document contains more than ${limits.maxNodes} JSON values.`,
      );
    }
    if (item.depth > limits.maxDepth) {
      throw new ResourceLimitError(
        `Document nesting exceeds the limit of ${limits.maxDepth}.`,
      );
    }
    if (typeof current === "string") {
      if (utf8Bytes(current) > limits.maxStringBytes) {
        throw new ResourceLimitError(
          `A string exceeds the limit of ${limits.maxStringBytes} bytes.`,
        );
      }
      continue;
    }
    if (
      current === null ||
      typeof current === "boolean" ||
      typeof current === "number"
    ) {
      continue;
    }
    if (typeof current !== "object") {
      throw new ResourceLimitError(
        `Value of type ${typeof current} is not JSON-compatible.`,
      );
    }
    if (active.has(current)) {
      throw new ResourceLimitError("Document contains a reference cycle.");
    }
    active.add(current);
    stack.push({ value: current, depth: item.depth, leaving: true });
    if (Array.isArray(current)) {
      if (current.length > limits.maxArrayItems) {
        throw new ResourceLimitError(
          `An array contains more than ${limits.maxArrayItems} items.`,
        );
      }
      for (let index = current.length - 1; index >= 0; index -= 1) {
        stack.push({ value: current[index], depth: item.depth + 1 });
      }
    } else {
      const entries = Object.entries(current);
      if (entries.length > limits.maxObjectProperties) {
        throw new ResourceLimitError(
          `An object contains more than ${limits.maxObjectProperties} properties.`,
        );
      }
      for (let index = entries.length - 1; index >= 0; index -= 1) {
        const [key, child] = entries[index];
        stack.push({ value: child, depth: item.depth + 1 });
        stack.push({ value: key, depth: item.depth + 1 });
      }
    }
  }
}

type AjvInstance = {
  addSchema(schema: JsonObject): void;
  getSchema(identifier: string): ValidateFunction | undefined;
  compile(schema: JsonObject): ValidateFunction;
};

const Ajv2020 = ((Ajv2020Import as unknown as { default?: unknown }).default ??
  Ajv2020Import) as unknown as new (
  options: Record<string, unknown>,
) => AjvInstance;
const addFormats = ((addFormatsImport as unknown as { default?: unknown }).default ??
  addFormatsImport) as unknown as (ajv: AjvInstance) => void;

function canonicalValue(value: JsonValue): JsonValue {
  if (Array.isArray(value)) return value.map(canonicalValue);
  if (typeof value === "object" && value !== null) {
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map((key) => [key, canonicalValue(value[key])]),
    );
  }
  return value;
}

function valuesMatch(left: JsonValue, right: JsonValue): boolean {
  return JSON.stringify(canonicalValue(left)) === JSON.stringify(canonicalValue(right));
}

export class BrowserBundle {
  readonly limits: ResourceLimits;
  private readonly files: Record<string, JsonObject>;

  constructor(
    files: Record<string, JsonObject>,
    limits: ResourceLimits = DEFAULT_RESOURCE_LIMITS,
  ) {
    this.files = files;
    this.limits = limits;
  }

  readJson(relativePath: string): JsonObject {
    const value = this.files[relativePath];
    if (!value) throw new Error(`Bundle file not found: ${relativePath}`);
    return value;
  }

  get catalogue(): JsonObject {
    return this.readJson("catalogue/catalogue.json");
  }

  profile(ref: string): JsonObject {
    if (!ref.startsWith(PROFILE_PREFIX)) {
      throw new Error(`Unknown profile reference: ${ref}`);
    }
    return this.readJson(`profiles/${ref.slice(PROFILE_PREFIX.length)}.json`);
  }

  profileSummary(ref: string): JsonObject | undefined {
    return (this.catalogue.profiles as JsonObject[]).find(
      (entry) => entry.ref === ref,
    );
  }

  schemaFiles(): string[] {
    return Object.keys(this.files)
      .filter((name) => name.startsWith("schemas/") && name.endsWith(".json"))
      .map((name) => name.slice("schemas/".length))
      .sort();
  }
}

let sharedBundle: BrowserBundle | undefined;
export function getBrowserBundle(): BrowserBundle {
  sharedBundle ??= new BrowserBundle(
    browserData.files as unknown as Record<string, JsonObject>,
  );
  return sharedBundle;
}

function validator(bundle: BrowserBundle): AjvInstance {
  const ajv = new Ajv2020({ allErrors: true, strict: false });
  addFormats(ajv);
  for (const name of bundle.schemaFiles()) {
    ajv.addSchema(bundle.readJson(`schemas/${name}`));
  }
  return ajv;
}

function schemaFindings(
  errors: ErrorObject[] | null | undefined,
): ValidationFinding[] {
  return (errors ?? []).map((error) => ({
    reason_code: "BMCS_SCHEMA_INVALID",
    message: error.message ?? error.keyword,
    path: error.instancePath,
    severity: "error",
  }));
}

function resourceFinding(error: unknown): ValidationFinding[] {
  return [
    {
      reason_code: "BMCS_RESOURCE_LIMIT_EXCEEDED",
      message: error instanceof Error ? error.message : String(error),
      path: "",
      severity: "error",
    },
  ];
}

function getDotted(document: JsonObject, path: string): JsonValue | undefined {
  let current: JsonValue = document;
  for (const segment of path.split(".")) {
    if (
      typeof current !== "object" ||
      current === null ||
      Array.isArray(current) ||
      !(segment in current)
    ) {
      return undefined;
    }
    current = current[segment];
  }
  return current;
}

export function validateObject(
  instance: JsonValue,
  schemaName: string,
  bundle = getBrowserBundle(),
): ValidationFinding[] {
  try {
    ensureJsonLimits(instance, bundle.limits);
  } catch (error) {
    return resourceFinding(error);
  }
  const normalizedName = schemaName.endsWith(".json")
    ? schemaName
    : `${schemaName}.json`;
  if (!bundle.schemaFiles().includes(normalizedName)) {
    throw new Error(`Unknown standard schema: ${schemaName}`);
  }
  const ajv = validator(bundle);
  const schema = bundle.readJson(`schemas/${normalizedName}`);
  const check = ajv.getSchema(schema.$id as string)!;
  check(instance);
  return schemaFindings(check.errors);
}

export function validateContract(
  contract: JsonObject,
  profileRefs: string[] = [],
  bundle = getBrowserBundle(),
): ValidationFinding[] {
  const findings = validateObject(contract, "port-contract.schema.json", bundle);
  if (profileRefs.length > bundle.limits.maxProfileRefs) {
    return [
      ...findings,
      ...resourceFinding(
        new ResourceLimitError(
          `Contract references more than ${bundle.limits.maxProfileRefs} profiles.`,
        ),
      ),
    ];
  }
  const ajv = validator(bundle);
  for (const ref of profileRefs) {
    let profile: JsonObject;
    try {
      profile = bundle.profile(ref);
    } catch {
      findings.push({
        reason_code: "BMCS_PROFILE_UNRESOLVED",
        message: `Profile not found in the installed bundle: ${ref}`,
        path: "/profile_refs",
        severity: "error",
      });
      continue;
    }
    for (const requirement of profile.requirements as JsonObject[]) {
      if (requirement.level !== "required") continue;
      const path = requirement.path as string;
      const value = getDotted(contract, path);
      if (value === undefined || value === null) {
        findings.push({
          reason_code: "BMCS_REQUIRED_MISSING",
          message: `Profile ${ref} requires '${path}', but it is missing.`,
          path: `/${path.replaceAll(".", "/")}`,
          severity: "error",
        });
        continue;
      }
      const check = ajv.compile(requirement.schema as JsonObject);
      if (!check(value)) {
        findings.push({
          reason_code: "BMCS_PROFILE_VALUE_INVALID",
          message: `${path}: ${check.errors?.[0]?.message ?? "value is invalid"}`,
          path: `/${path.replaceAll(".", "/")}`,
          severity: "error",
        });
      }
    }
  }
  return findings;
}

function cloneJson<T extends JsonValue>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function mergeRefinement(
  base: JsonObject,
  refinement: JsonObject,
  path = "",
): { merged: JsonObject; conflicts: string[] } {
  const merged = cloneJson(base);
  const conflicts: string[] = [];
  for (const [key, value] of Object.entries(refinement)) {
    const childPath = `${path}/${key}`;
    const existing = merged[key];
    if (!(key in merged)) {
      merged[key] = cloneJson(value);
    } else if (
      typeof existing === "object" &&
      existing !== null &&
      !Array.isArray(existing) &&
      typeof value === "object" &&
      value !== null &&
      !Array.isArray(value)
    ) {
      const nested = mergeRefinement(
        existing as JsonObject,
        value as JsonObject,
        childPath,
      );
      merged[key] = nested.merged;
      conflicts.push(...nested.conflicts);
    } else if (!valuesMatch(existing, value)) {
      conflicts.push(childPath);
    }
  }
  return { merged, conflicts };
}

export function validateManifest(
  manifest: JsonObject,
  bundle = getBrowserBundle(),
): ValidationFinding[] {
  if (!("compatibility" in manifest)) return [];
  const findings = validateObject(
    manifest,
    "manifest-extension.schema.json",
    bundle,
  );
  const compatibility = manifest.compatibility as JsonObject;
  const imports = new Map<string, JsonObject>();
  for (const item of (compatibility.profiles ?? []) as JsonObject[]) {
    imports.set(item.ref as string, item);
  }
  for (const [ref, imported] of imports) {
    const expected = bundle.profileSummary(ref);
    if (!expected) {
      findings.push({
        reason_code: "BMCS_PROFILE_UNRESOLVED",
        message: `Profile not found in the installed bundle: ${ref}`,
        path: "/compatibility/profiles",
        severity: "error",
      });
    } else if (imported.sha256 !== expected.sha256) {
      findings.push({
        reason_code: "BMCS_DIGEST_MISMATCH",
        message: `The sha256 for ${ref} doesn't match the installed profile.`,
        path: "/compatibility/profiles",
        severity: "error",
      });
    }
  }

  const io = manifest.io as JsonObject;
  for (const direction of ["inputs", "outputs"]) {
    for (const [index, rawPort] of (
      (io?.[direction] ?? []) as JsonObject[]
    ).entries()) {
      const contract = rawPort.contract as JsonObject | undefined;
      const acceptedProfiles = (rawPort.accepted_profiles ?? []) as JsonObject[];
      if (!contract) {
        for (const [acceptedIndex, accepted] of acceptedProfiles.entries()) {
          if (accepted.contract) {
            findings.push({
              reason_code: "BMCS_REFINEMENT_WITHOUT_BASE",
              message:
                "An accepted profile contract must refine an input-level contract.",
              path: `/io/${direction}/${index}/accepted_profiles/${acceptedIndex}/contract`,
              severity: "error",
            });
          }
        }
        continue;
      }
      const refs = (contract.profile_refs ?? []) as string[];
      for (const ref of refs) {
        if (!imports.has(ref)) {
          findings.push({
            reason_code: "BMCS_PROFILE_NOT_IMPORTED",
            message: `This port uses ${ref}, but it isn't listed in compatibility.profiles.`,
            path: `/io/${direction}/${index}/contract/profile_refs`,
            severity: "error",
          });
        }
      }
      findings.push(...validateContract(contract, refs, bundle));
      for (const [acceptedIndex, accepted] of acceptedProfiles.entries()) {
        const refinement = accepted.contract as JsonObject | undefined;
        if (!refinement) continue;
        const { merged, conflicts } = mergeRefinement(contract, refinement);
        for (const conflict of conflicts) {
          findings.push({
            reason_code: "BMCS_REFINEMENT_WEAKENS_CONTRACT",
            message: `The accepted profile changes the common invariant at ${conflict}.`,
            path: `/io/${direction}/${index}/accepted_profiles/${acceptedIndex}/contract${conflict}`,
            severity: "error",
          });
        }
        for (const item of validateContract(merged, refs, bundle)) {
          findings.push({
            ...item,
            path: `/io/${direction}/${index}/accepted_profiles/${acceptedIndex}/contract${item.path}`,
          });
        }
      }
    }
  }
  return findings;
}

export function parseYaml(
  text: string,
  limits: ResourceLimits = DEFAULT_RESOURCE_LIMITS,
): JsonObject {
  if (utf8Bytes(text) > limits.maxDocumentBytes) {
    throw new ResourceLimitError(
      `Document is ${utf8Bytes(text)} bytes; the limit is ${limits.maxDocumentBytes} bytes.`,
    );
  }
  const parsed = YAML.parse(text, { maxAliasCount: 100 }) as JsonValue;
  ensureJsonLimits(parsed, limits);
  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    throw new TypeError("The YAML document must contain an object at its root.");
  }
  return parsed;
}

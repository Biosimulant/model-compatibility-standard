import Ajv2020Import from "ajv/dist/2020.js";
import addFormatsImport from "ajv-formats";
import YAML from "yaml";
import browserData from "./browser-data.json" with { type: "json" };
export const STANDARD = "https://biosimulant.com/standards/model-compatibility/v0.1";
const PROFILE_PREFIX = `${STANDARD.replace("/v0.1", "")}/profiles/`;
export const DEFAULT_RESOURCE_LIMITS = {
    maxDocumentBytes: 4 * 1024 * 1024,
    maxDepth: 64,
    maxNodes: 200_000,
    maxStringBytes: 1024 * 1024,
    maxArrayItems: 100_000,
    maxObjectProperties: 100_000,
    maxProfileRefs: 100,
    maxRules: 10_000,
};
export class ResourceLimitError extends Error {
}
function utf8Bytes(value) {
    return new TextEncoder().encode(value).byteLength;
}
export function ensureJsonLimits(value, limits = DEFAULT_RESOURCE_LIMITS) {
    let nodes = 0;
    const active = new Set();
    const stack = [
        { value, depth: 0 },
    ];
    while (stack.length) {
        const item = stack.pop();
        const current = item.value;
        if (item.leaving) {
            active.delete(current);
            continue;
        }
        nodes += 1;
        if (nodes > limits.maxNodes) {
            throw new ResourceLimitError(`Document contains more than ${limits.maxNodes} JSON values.`);
        }
        if (item.depth > limits.maxDepth) {
            throw new ResourceLimitError(`Document nesting exceeds the limit of ${limits.maxDepth}.`);
        }
        if (typeof current === "string") {
            if (utf8Bytes(current) > limits.maxStringBytes) {
                throw new ResourceLimitError(`A string exceeds the limit of ${limits.maxStringBytes} bytes.`);
            }
            continue;
        }
        if (current === null ||
            typeof current === "boolean" ||
            typeof current === "number") {
            continue;
        }
        if (typeof current !== "object") {
            throw new ResourceLimitError(`Value of type ${typeof current} is not JSON-compatible.`);
        }
        if (active.has(current)) {
            throw new ResourceLimitError("Document contains a reference cycle.");
        }
        active.add(current);
        stack.push({ value: current, depth: item.depth, leaving: true });
        if (Array.isArray(current)) {
            if (current.length > limits.maxArrayItems) {
                throw new ResourceLimitError(`An array contains more than ${limits.maxArrayItems} items.`);
            }
            for (let index = current.length - 1; index >= 0; index -= 1) {
                stack.push({ value: current[index], depth: item.depth + 1 });
            }
        }
        else {
            const entries = Object.entries(current);
            if (entries.length > limits.maxObjectProperties) {
                throw new ResourceLimitError(`An object contains more than ${limits.maxObjectProperties} properties.`);
            }
            for (let index = entries.length - 1; index >= 0; index -= 1) {
                const [key, child] = entries[index];
                stack.push({ value: child, depth: item.depth + 1 });
                stack.push({ value: key, depth: item.depth + 1 });
            }
        }
    }
}
const Ajv2020 = (Ajv2020Import.default ??
    Ajv2020Import);
const addFormats = (addFormatsImport.default ??
    addFormatsImport);
function canonicalValue(value) {
    if (Array.isArray(value))
        return value.map(canonicalValue);
    if (typeof value === "object" && value !== null) {
        return Object.fromEntries(Object.keys(value)
            .sort()
            .map((key) => [key, canonicalValue(value[key])]));
    }
    return value;
}
function valuesMatch(left, right) {
    return JSON.stringify(canonicalValue(left)) === JSON.stringify(canonicalValue(right));
}
export class BrowserBundle {
    limits;
    files;
    constructor(files, limits = DEFAULT_RESOURCE_LIMITS) {
        this.files = files;
        this.limits = limits;
    }
    readJson(relativePath) {
        const value = this.files[relativePath];
        if (!value)
            throw new Error(`Bundle file not found: ${relativePath}`);
        return value;
    }
    get catalogue() {
        return this.readJson("catalogue/catalogue.json");
    }
    profile(ref) {
        if (!ref.startsWith(PROFILE_PREFIX)) {
            throw new Error(`Unknown profile reference: ${ref}`);
        }
        return this.readJson(`profiles/${ref.slice(PROFILE_PREFIX.length)}.json`);
    }
    profileSummary(ref) {
        return this.catalogue.profiles.find((entry) => entry.ref === ref);
    }
    schemaFiles() {
        return Object.keys(this.files)
            .filter((name) => name.startsWith("schemas/") && name.endsWith(".json"))
            .map((name) => name.slice("schemas/".length))
            .sort();
    }
}
let sharedBundle;
export function getBrowserBundle() {
    sharedBundle ??= new BrowserBundle(browserData.files);
    return sharedBundle;
}
function validator(bundle) {
    const ajv = new Ajv2020({ allErrors: true, strict: false });
    addFormats(ajv);
    for (const name of bundle.schemaFiles()) {
        ajv.addSchema(bundle.readJson(`schemas/${name}`));
    }
    return ajv;
}
function schemaFindings(errors) {
    return (errors ?? []).map((error) => ({
        reason_code: "BMCS_SCHEMA_INVALID",
        message: error.message ?? error.keyword,
        path: error.instancePath,
        severity: "error",
    }));
}
function resourceFinding(error) {
    return [
        {
            reason_code: "BMCS_RESOURCE_LIMIT_EXCEEDED",
            message: error instanceof Error ? error.message : String(error),
            path: "",
            severity: "error",
        },
    ];
}
function getDotted(document, path) {
    let current = document;
    for (const segment of path.split(".")) {
        if (typeof current !== "object" ||
            current === null ||
            Array.isArray(current) ||
            !(segment in current)) {
            return undefined;
        }
        current = current[segment];
    }
    return current;
}
export function validateObject(instance, schemaName, bundle = getBrowserBundle()) {
    try {
        ensureJsonLimits(instance, bundle.limits);
    }
    catch (error) {
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
    const check = ajv.getSchema(schema.$id);
    check(instance);
    return schemaFindings(check.errors);
}
export function validateContract(contract, profileRefs = [], bundle = getBrowserBundle()) {
    const findings = validateObject(contract, "port-contract.schema.json", bundle);
    if (profileRefs.length > bundle.limits.maxProfileRefs) {
        return [
            ...findings,
            ...resourceFinding(new ResourceLimitError(`Contract references more than ${bundle.limits.maxProfileRefs} profiles.`)),
        ];
    }
    const ajv = validator(bundle);
    for (const ref of profileRefs) {
        let profile;
        try {
            profile = bundle.profile(ref);
        }
        catch {
            findings.push({
                reason_code: "BMCS_PROFILE_UNRESOLVED",
                message: `Profile not found in the installed bundle: ${ref}`,
                path: "/profile_refs",
                severity: "error",
            });
            continue;
        }
        for (const requirement of profile.requirements) {
            if (requirement.level !== "required")
                continue;
            const path = requirement.path;
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
            const check = ajv.compile(requirement.schema);
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
function cloneJson(value) {
    return JSON.parse(JSON.stringify(value));
}
function mergeRefinement(base, refinement, path = "") {
    const merged = cloneJson(base);
    const conflicts = [];
    for (const [key, value] of Object.entries(refinement)) {
        const childPath = `${path}/${key}`;
        const existing = merged[key];
        if (!(key in merged)) {
            merged[key] = cloneJson(value);
        }
        else if (typeof existing === "object" &&
            existing !== null &&
            !Array.isArray(existing) &&
            typeof value === "object" &&
            value !== null &&
            !Array.isArray(value)) {
            const nested = mergeRefinement(existing, value, childPath);
            merged[key] = nested.merged;
            conflicts.push(...nested.conflicts);
        }
        else if (!valuesMatch(existing, value)) {
            conflicts.push(childPath);
        }
    }
    return { merged, conflicts };
}
export function validateManifest(manifest, bundle = getBrowserBundle()) {
    if (!("compatibility" in manifest))
        return [];
    const findings = validateObject(manifest, "manifest-extension.schema.json", bundle);
    const compatibility = manifest.compatibility;
    const imports = new Map();
    for (const item of (compatibility.profiles ?? [])) {
        imports.set(item.ref, item);
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
        }
        else if (imported.sha256 !== expected.sha256) {
            findings.push({
                reason_code: "BMCS_DIGEST_MISMATCH",
                message: `The sha256 for ${ref} doesn't match the installed profile.`,
                path: "/compatibility/profiles",
                severity: "error",
            });
        }
    }
    const io = manifest.io;
    for (const direction of ["inputs", "outputs"]) {
        for (const [index, rawPort] of (io?.[direction] ?? []).entries()) {
            const contract = rawPort.contract;
            const acceptedProfiles = (rawPort.accepted_profiles ?? []);
            if (!contract) {
                for (const [acceptedIndex, accepted] of acceptedProfiles.entries()) {
                    if (accepted.contract) {
                        findings.push({
                            reason_code: "BMCS_REFINEMENT_WITHOUT_BASE",
                            message: "An accepted profile contract must refine an input-level contract.",
                            path: `/io/${direction}/${index}/accepted_profiles/${acceptedIndex}/contract`,
                            severity: "error",
                        });
                    }
                }
                continue;
            }
            const refs = (contract.profile_refs ?? []);
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
                const refinement = accepted.contract;
                if (!refinement)
                    continue;
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
export function parseYaml(text, limits = DEFAULT_RESOURCE_LIMITS) {
    if (utf8Bytes(text) > limits.maxDocumentBytes) {
        throw new ResourceLimitError(`Document is ${utf8Bytes(text)} bytes; the limit is ${limits.maxDocumentBytes} bytes.`);
    }
    const parsed = YAML.parse(text, { maxAliasCount: 100 });
    ensureJsonLimits(parsed, limits);
    if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
        throw new TypeError("The YAML document must contain an object at its root.");
    }
    return parsed;
}

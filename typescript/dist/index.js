import { createHash } from "node:crypto";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import Ajv2020Import from "ajv/dist/2020.js";
import addFormatsImport from "ajv-formats";
import canonicalizeImport from "canonicalize";
import YAML from "yaml";
import { convertUnit, parseUnit } from "./units.js";
export const STANDARD = "https://biosimulant.com/standards/model-compatibility/v0.1";
const PROFILE_PREFIX = "https://biosimulant.com/standards/model-compatibility/profiles/";
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
    return Buffer.byteLength(value, "utf8");
}
export function ensureJsonLimits(value, limits = DEFAULT_RESOURCE_LIMITS) {
    let nodes = 0;
    const active = new Set();
    const stack = [{ value, depth: 0 }];
    while (stack.length) {
        const item = stack.pop();
        const current = item.value;
        if (item.leaving) {
            active.delete(current);
            continue;
        }
        nodes += 1;
        if (nodes > limits.maxNodes)
            throw new ResourceLimitError(`Document contains more than ${limits.maxNodes} JSON values.`);
        if (item.depth > limits.maxDepth)
            throw new ResourceLimitError(`Document nesting exceeds the limit of ${limits.maxDepth}.`);
        if (typeof current === "string") {
            if (utf8Bytes(current) > limits.maxStringBytes)
                throw new ResourceLimitError(`A string exceeds the limit of ${limits.maxStringBytes} bytes.`);
            continue;
        }
        if (current === null || typeof current === "boolean" || typeof current === "number")
            continue;
        if (typeof current !== "object")
            throw new ResourceLimitError(`Value of type ${typeof current} is not JSON-compatible.`);
        if (active.has(current))
            throw new ResourceLimitError("Document contains a reference cycle.");
        active.add(current);
        stack.push({ value: current, depth: item.depth, leaving: true });
        if (Array.isArray(current)) {
            if (current.length > limits.maxArrayItems)
                throw new ResourceLimitError(`An array contains more than ${limits.maxArrayItems} items.`);
            for (let index = current.length - 1; index >= 0; index -= 1)
                stack.push({ value: current[index], depth: item.depth + 1 });
        }
        else {
            const entries = Object.entries(current);
            if (entries.length > limits.maxObjectProperties)
                throw new ResourceLimitError(`An object contains more than ${limits.maxObjectProperties} properties.`);
            for (let index = entries.length - 1; index >= 0; index -= 1) {
                const [key, child] = entries[index];
                stack.push({ value: child, depth: item.depth + 1 });
                stack.push({ value: key, depth: item.depth + 1 });
            }
        }
    }
}
function moduleSpecRoot() {
    return join(dirname(fileURLToPath(import.meta.url)), "..", "..", "spec", "v0.1");
}
export class Bundle {
    root;
    limits;
    cache = new Map();
    constructor(root = moduleSpecRoot(), limits = DEFAULT_RESOURCE_LIMITS) {
        this.root = root;
        this.limits = limits;
    }
    path(relativePath) {
        const target = resolve(this.root, relativePath);
        const child = relative(resolve(this.root), target);
        if (!child || child === ".." || child.startsWith(`..${sep}`))
            throw new Error(`Bundle path must be relative and contained in the bundle: ${relativePath}`);
        return target;
    }
    readJson(relativePath) {
        const cached = this.cache.get(relativePath);
        if (cached)
            return cached;
        const target = this.path(relativePath);
        const size = statSync(target).size;
        if (size > this.limits.maxDocumentBytes)
            throw new ResourceLimitError(`Bundle file ${relativePath} is ${size} bytes; the limit is ${this.limits.maxDocumentBytes} bytes.`);
        const value = JSON.parse(readFileSync(target, "utf8"));
        ensureJsonLimits(value, this.limits);
        this.cache.set(relativePath, value);
        return value;
    }
    get manifest() {
        return this.readJson("bundle.manifest.json");
    }
    get catalogue() {
        return this.readJson("catalogue/catalogue.json");
    }
    profile(ref) {
        if (!ref.startsWith(PROFILE_PREFIX))
            throw new Error(`Unknown profile reference: ${ref}`);
        const relative = ref.slice(PROFILE_PREFIX.length);
        return this.readJson(`profiles/${relative}.json`);
    }
    profileSummary(ref) {
        return this.catalogue.profiles.find((entry) => entry.ref === ref);
    }
    schemaFiles() {
        return readdirSync(join(this.root, "schemas")).filter((name) => name.endsWith(".json")).sort();
    }
    units() {
        try {
            return this.readJson("rules/units.json");
        }
        catch {
            return undefined;
        }
    }
    quantityKinds() {
        try {
            return (this.readJson("rules/quantity-kinds.json").kinds ?? {});
        }
        catch {
            return {};
        }
    }
    verifyIntegrity() {
        const manifest = this.manifest;
        const { bundle_sha256: declared, ...unsigned } = manifest;
        if (declared !== digest(unsigned))
            throw new Error("The bundle manifest digest does not match its contents.");
        const seen = new Set();
        for (const raw of manifest.files) {
            const relativePath = raw.path;
            if (typeof relativePath !== "string" || seen.has(relativePath))
                throw new Error("The bundle manifest contains an invalid or duplicate file path.");
            seen.add(relativePath);
            const data = readFileSync(this.path(relativePath));
            if (data.byteLength !== raw.size_bytes)
                throw new Error(`Bundle file size does not match the manifest: ${relativePath}`);
            const actual = `sha256:${createHash("sha256").update(data).digest("hex")}`;
            if (actual !== raw.sha256)
                throw new Error(`Bundle file digest does not match the manifest: ${relativePath}`);
        }
    }
}
let sharedBundle;
export function getBundle() {
    sharedBundle ??= new Bundle();
    return sharedBundle;
}
const canonicalizeFunction = (canonicalizeImport.default ?? canonicalizeImport);
export function canonicalJson(value) {
    const encoded = canonicalizeFunction(value);
    if (encoded === undefined)
        throw new TypeError("Value can't be serialized as canonical JSON");
    return encoded;
}
export function digest(value) {
    return `sha256:${createHash("sha256").update(canonicalJson(value), "utf8").digest("hex")}`;
}
const Ajv2020 = (Ajv2020Import.default ?? Ajv2020Import);
const addFormats = (addFormatsImport.default ?? addFormatsImport);
function validator(bundle) {
    const ajv = new Ajv2020({ allErrors: true, strict: false });
    addFormats(ajv);
    for (const name of bundle.schemaFiles())
        ajv.addSchema(bundle.readJson(`schemas/${name}`));
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
    return [{ reason_code: "BMCS_RESOURCE_LIMIT_EXCEEDED", message: error instanceof Error ? error.message : String(error), path: "", severity: "error" }];
}
function getDotted(document, path) {
    let current = document;
    for (const segment of path.split(".")) {
        if (typeof current !== "object" || current === null || Array.isArray(current) || !(segment in current))
            return undefined;
        current = current[segment];
    }
    return current;
}
function getPointer(document, pointer) {
    let current = document;
    for (const raw of pointer.slice(1).split("/")) {
        const segment = raw.replaceAll("~1", "/").replaceAll("~0", "~");
        if (Array.isArray(current) && /^\d+$/.test(segment) && Number(segment) < current.length)
            current = current[Number(segment)];
        else if (typeof current === "object" && current !== null && !Array.isArray(current) && segment in current)
            current = current[segment];
        else
            return undefined;
    }
    return current;
}
export function validateContract(contract, profileRefs = [], bundle = getBundle()) {
    try {
        ensureJsonLimits(contract, bundle.limits);
    }
    catch (error) {
        return resourceFinding(error);
    }
    const ajv = validator(bundle);
    const schema = bundle.readJson("schemas/port-contract.schema.json");
    const check = ajv.getSchema(schema.$id);
    check(contract);
    const findings = schemaFindings(check.errors);
    if (profileRefs.length > bundle.limits.maxProfileRefs)
        return [...findings, ...resourceFinding(new ResourceLimitError(`Contract references more than ${bundle.limits.maxProfileRefs} profiles.`))];
    for (const ref of profileRefs) {
        let profile;
        try {
            profile = bundle.profile(ref);
        }
        catch {
            findings.push({ reason_code: "BMCS_PROFILE_UNRESOLVED", message: `Profile not found in the installed bundle: ${ref}`, path: "/profile_refs", severity: "error" });
            continue;
        }
        const rules = profile.comparison_rules;
        if (rules.length > bundle.limits.maxRules) {
            findings.push({ reason_code: "BMCS_RESOURCE_LIMIT_EXCEEDED", message: `Profile ${ref} contains more than ${bundle.limits.maxRules} comparison rules.`, path: "/profile_refs", severity: "error" });
            continue;
        }
        for (const requirement of profile.requirements) {
            if (requirement.level !== "required")
                continue;
            const path = requirement.path;
            if (path.includes("[]")) {
                // "dimensions.axes[].unit" means every axis declares a unit, so the requirement is checked
                // once per member and reports which member failed.
                const [head, tail] = path.split("[]");
                const containerPath = head.replace(/\.$/, "");
                const leaf = tail.replace(/^\./, "");
                const pointer = `/${containerPath.replaceAll(".", "/")}`;
                const container = getDotted(contract, containerPath);
                if (!Array.isArray(container) || !container.length) {
                    findings.push({ reason_code: "BMCS_REQUIRED_MISSING", message: `Profile ${ref} requires '${path}', but it is missing.`, path: pointer, severity: "error" });
                    continue;
                }
                const checkMember = ajv.compile(requirement.schema);
                container.forEach((member, index) => {
                    const memberValue = member && typeof member === "object" && !Array.isArray(member) ? getDotted(member, leaf) : undefined;
                    const memberPointer = `${pointer}/${index}/${leaf.replaceAll(".", "/")}`;
                    if (memberValue === undefined || memberValue === null) {
                        findings.push({ reason_code: "BMCS_REQUIRED_MISSING", message: `Profile ${ref} requires '${path}', but member ${index} does not declare it.`, path: memberPointer, severity: "error" });
                        return;
                    }
                    if (!checkMember(memberValue)) {
                        findings.push({ reason_code: "BMCS_PROFILE_VALUE_INVALID", message: `${path}[${index}]: ${checkMember.errors?.[0]?.message ?? "value is invalid"}`, path: memberPointer, severity: "error" });
                    }
                });
                continue;
            }
            const value = getDotted(contract, path);
            if (value === undefined || value === null) {
                findings.push({ reason_code: "BMCS_REQUIRED_MISSING", message: `Profile ${ref} requires '${path}', but it is missing.`, path: `/${path.replaceAll(".", "/")}`, severity: "error" });
                continue;
            }
            const checkRequirement = ajv.compile(requirement.schema);
            if (!checkRequirement(value)) {
                findings.push({ reason_code: "BMCS_PROFILE_VALUE_INVALID", message: `${path}: ${checkRequirement.errors?.[0]?.message ?? "value is invalid"}`, path: `/${path.replaceAll(".", "/")}`, severity: "error" });
            }
        }
        findings.push(...unitFindings(bundle, profile, contract));
    }
    return findings;
}
/**
 * Check a declared unit against the profile's quantity kind.
 *
 * A unit alone does not identify a quantity: hertz and becquerel are both per second, and a
 * Hounsfield unit is dimensionless like a bare ratio. Mirrors _unit_findings in the Python
 * implementation.
 */
function normalised(contract, bundle) {
    // A caller may pass a minimal bundle that carries only the profiles it needs.
    if (contract === null)
        return null;
    try {
        return normalizeContract(contract, bundle);
    }
    catch {
        return contract;
    }
}
/** A declared unit that cannot belong to the profile's quantity kind. */
function unitKindErrors(bundle, profile, contract) {
    const table = typeof bundle.units === "function" ? bundle.units() : undefined;
    const measurement = contract.measurement;
    const unit = measurement?.unit;
    const quantity = profile.fixed?.measurement?.quantity;
    if (!table || typeof unit !== "string" || typeof quantity !== "string")
        return [];
    const kindId = quantity.split("/").pop();
    const kinds = typeof bundle.quantityKinds === "function" ? bundle.quantityKinds() : {};
    const kind = kinds[kindId];
    if (!kind)
        return [];
    let declared;
    try {
        declared = parseUnit(unit, table);
    }
    catch {
        return [];
    }
    const allowed = kind.allowed_units;
    if (allowed?.length && !allowed.includes(unit))
        return [`${unit} is not one of the units ${kindId} accepts`];
    const canonical = kind.canonical_unit;
    if (canonical) {
        try {
            const expected = parseUnit(canonical, table);
            if (JSON.stringify(declared.dimension) !== JSON.stringify(expected.dimension)) {
                return [`${unit} does not have the dimension of ${kindId} (${canonical})`];
            }
        }
        catch {
            return [];
        }
    }
    return [];
}
function unitFindings(bundle, profile, contract) {
    const table = typeof bundle.units === "function" ? bundle.units() : undefined;
    const value = getDotted(contract, "measurement.unit");
    if (!table || value === undefined || value === null)
        return [];
    const path = "/measurement/unit";
    if (typeof value !== "string")
        return [{ reason_code: "BMCS_UNIT_INVALID", message: "measurement.unit must be a UCUM expression.", path, severity: "error" }];
    let declared;
    try {
        declared = parseUnit(value, table);
    }
    catch (error) {
        return [{ reason_code: "BMCS_UNIT_INVALID", message: `measurement.unit: ${error.message}`, path, severity: "error" }];
    }
    const quantity = getDotted((profile.fixed ?? {}), "measurement.quantity");
    if (typeof quantity !== "string")
        return [];
    const kindId = quantity.split("/").pop();
    const kind = bundle.quantityKinds()[kindId];
    if (!kind)
        return [];
    const allowed = kind.allowed_units;
    if (allowed?.length && !allowed.includes(value)) {
        return [{ reason_code: "BMCS_UNIT_NOT_ALLOWED", message: `measurement.unit: ${value} is not one of the units ${kindId} accepts (${allowed.join(", ")}).`, path, severity: "error" }];
    }
    const forbidden = new Set(kind.forbidden_unit_properties ?? []);
    if (forbidden.size) {
        for (const code of [...declared.codes].sort()) {
            const property = table.units[code]?.property;
            if (property && forbidden.has(property)) {
                return [{ reason_code: "BMCS_UNIT_NOT_ALLOWED", message: `measurement.unit: ${code} measures ${property}, which ${kindId} does not.`, path, severity: "error" }];
            }
        }
    }
    const canonical = kind.canonical_unit;
    if (canonical) {
        try {
            const expected = parseUnit(canonical, table);
            if (JSON.stringify(declared.dimension) !== JSON.stringify(expected.dimension)) {
                return [{ reason_code: "BMCS_UNIT_DIMENSION_MISMATCH", message: `measurement.unit: ${value} does not have the dimension of ${kindId} (${canonical}).`, path, severity: "error" }];
            }
        }
        catch {
            return [];
        }
    }
    return [];
}
export function validateObject(instance, schemaName, bundle = getBundle()) {
    try {
        ensureJsonLimits(instance, bundle.limits);
    }
    catch (error) {
        return resourceFinding(error);
    }
    const ajv = validator(bundle);
    const normalizedName = schemaName.endsWith(".json") ? schemaName : `${schemaName}.json`;
    if (!bundle.schemaFiles().includes(normalizedName))
        throw new Error(`Unknown standard schema: ${schemaName}`);
    const schema = bundle.readJson(`schemas/${normalizedName}`);
    const check = ajv.getSchema(schema.$id);
    check(instance);
    return schemaFindings(check.errors);
}
export function validateManifest(manifest, bundle = getBundle()) {
    if (!("compatibility" in manifest))
        return [];
    try {
        ensureJsonLimits(manifest, bundle.limits);
    }
    catch (error) {
        return resourceFinding(error);
    }
    const ajv = validator(bundle);
    const schema = bundle.readJson("schemas/manifest-extension.schema.json");
    const check = ajv.getSchema(schema.$id);
    check(manifest);
    const findings = schemaFindings(check.errors);
    const compatibility = manifest.compatibility;
    const imports = new Map();
    for (const item of (compatibility.profiles ?? []))
        imports.set(item.ref, item);
    for (const [ref, imported] of imports) {
        const expected = bundle.profileSummary(ref);
        if (!expected)
            findings.push({ reason_code: "BMCS_PROFILE_UNRESOLVED", message: `Profile not found in the installed bundle: ${ref}`, path: "/compatibility/profiles", severity: "error" });
        else if (imported.sha256 !== expected.sha256)
            findings.push({ reason_code: "BMCS_DIGEST_MISMATCH", message: `The sha256 for ${ref} doesn't match the installed profile.`, path: "/compatibility/profiles", severity: "error" });
    }
    const io = manifest.io;
    for (const direction of ["inputs", "outputs"]) {
        for (const [index, rawPort] of (io?.[direction] ?? []).entries()) {
            const contract = rawPort.contract;
            const acceptedProfiles = (rawPort.accepted_profiles ?? []);
            if (!contract) {
                for (const [acceptedIndex, accepted] of acceptedProfiles.entries()) {
                    if (accepted.contract)
                        findings.push({ reason_code: "BMCS_REFINEMENT_WITHOUT_BASE", message: "An accepted profile contract must refine an input-level contract.", path: `/io/${direction}/${index}/accepted_profiles/${acceptedIndex}/contract`, severity: "error" });
                }
                continue;
            }
            const refs = (contract.profile_refs ?? []);
            for (const ref of refs)
                if (!imports.has(ref))
                    findings.push({ reason_code: "BMCS_PROFILE_NOT_IMPORTED", message: `This port uses ${ref}, but it isn't listed in compatibility.profiles.`, path: `/io/${direction}/${index}/contract/profile_refs`, severity: "error" });
            findings.push(...validateContract(contract, refs, bundle));
            for (const [acceptedIndex, accepted] of acceptedProfiles.entries()) {
                const refinement = accepted.contract;
                if (!refinement)
                    continue;
                const { merged, conflicts } = mergeRefinement(contract, refinement);
                for (const conflict of conflicts)
                    findings.push({ reason_code: "BMCS_REFINEMENT_WEAKENS_CONTRACT", message: `The accepted profile changes the common invariant at ${conflict}.`, path: `/io/${direction}/${index}/accepted_profiles/${acceptedIndex}/contract${conflict}`, severity: "error" });
                for (const item of validateContract(merged, refs, bundle))
                    findings.push({ ...item, path: `/io/${direction}/${index}/accepted_profiles/${acceptedIndex}/contract${item.path}` });
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
        if (!(key in merged))
            merged[key] = cloneJson(value);
        else if (typeof existing === "object" && existing !== null && !Array.isArray(existing) && typeof value === "object" && value !== null && !Array.isArray(value)) {
            const nested = mergeRefinement(existing, value, childPath);
            merged[key] = nested.merged;
            conflicts.push(...nested.conflicts);
        }
        else if (canonicalJson(existing) !== canonicalJson(value))
            conflicts.push(childPath);
    }
    return { merged, conflicts };
}
function finding(dimension, state, reason, explanation, evidence) {
    return { dimension, state, severity: state === "INCOMPATIBLE" ? "error" : "info", reason_code: reason, explanation, ...(evidence === undefined ? {} : { evidence }) };
}
function rulesFor(refs, bundle) {
    const result = [];
    const seen = new Set();
    for (const ref of [...new Set(refs)].sort()) {
        for (const rule of bundle.profile(ref).comparison_rules) {
            const key = `${rule.source}\0${rule.target}\0${rule.operator}`;
            if (!seen.has(key)) {
                seen.add(key);
                result.push(rule);
            }
        }
    }
    return result;
}
function verifiedSnapshots(values = []) {
    const result = new Map();
    for (const snapshot of values) {
        const { sha256: declared, ...unsigned } = snapshot;
        if (typeof snapshot.ref === "string" && declared === digest(unsigned))
            result.set(snapshot.ref, snapshot);
    }
    return result;
}
function snapshotFor(rule, snapshots) {
    const parameters = (rule.parameters ?? {});
    const ref = parameters.snapshot_ref;
    const expected = parameters.snapshot_sha256;
    const snapshot = typeof ref === "string" ? snapshots.get(ref) : undefined;
    return snapshot && (expected === undefined || snapshot.sha256 === expected) ? snapshot : undefined;
}
function termEquivalent(source, target, snapshot) {
    if (canonicalJson(source) === canonicalJson(target))
        return true;
    const graph = new Map();
    for (const raw of (snapshot.equivalences ?? [])) {
        if (!Array.isArray(raw) || raw.length !== 2 || !raw.every((item) => typeof item === "string"))
            continue;
        graph.set(raw[0], new Set([...(graph.get(raw[0]) ?? []), raw[1]]));
        graph.set(raw[1], new Set([...(graph.get(raw[1]) ?? []), raw[0]]));
    }
    const pending = typeof source === "string" ? [source] : [];
    const seen = new Set();
    while (pending.length) {
        const current = pending.pop();
        if (current === target)
            return true;
        if (seen.has(current))
            continue;
        seen.add(current);
        pending.push(...[...(graph.get(current) ?? [])].filter((item) => !seen.has(item)).sort());
    }
    return false;
}
function termSubsumes(source, target, snapshot) {
    if (canonicalJson(source) === canonicalJson(target))
        return true;
    const parents = new Map();
    for (const raw of (snapshot.subsumptions ?? [])) {
        if (typeof raw.child !== "string" || typeof raw.parent !== "string")
            continue;
        parents.set(raw.child, new Set([...(parents.get(raw.child) ?? []), raw.parent]));
    }
    const pending = typeof source === "string" ? [source] : [];
    const seen = new Set();
    while (pending.length) {
        const current = pending.pop();
        if (current === target)
            return true;
        if (seen.has(current))
            continue;
        seen.add(current);
        pending.push(...[...(parents.get(current) ?? [])].filter((item) => !seen.has(item)).sort());
    }
    return false;
}
function mappingMatches(source, target, snapshot, bijective) {
    if (!Array.isArray(source) || !Array.isArray(target))
        return false;
    const allowedTargets = new Set(target.map((value) => canonicalJson(value)));
    const table = new Map();
    for (const raw of (snapshot.mappings ?? [])) {
        if (raw.source === undefined)
            continue;
        const rawTargets = Array.isArray(raw.targets) ? raw.targets : [raw.target];
        table.set(canonicalJson(raw.source), rawTargets.filter((value) => value !== undefined).map((value) => canonicalJson(value)));
    }
    const mapped = [];
    for (const value of source) {
        const candidates = (table.get(canonicalJson(value)) ?? []).filter((item) => allowedTargets.has(item));
        if (!candidates.length || (bijective && candidates.length !== 1))
            return false;
        mapped.push(...candidates);
    }
    return !bijective || (mapped.length === new Set(mapped).size && mapped.length === allowedTargets.size && mapped.every((item) => allowedTargets.has(item)));
}
function safePattern(pattern, value) {
    if (typeof pattern !== "string" || typeof value !== "string" || pattern.length > 256 || value.length > 4096)
        return [false, "invalid"];
    if (pattern.includes("(?") || /\\[1-9]/u.test(pattern) || /[+*?][+*?]/u.test(pattern))
        return [false, "invalid"];
    try {
        return [new RegExp(`^(?:${pattern})$`, "u").test(value), undefined];
    }
    catch {
        return [false, "invalid"];
    }
}
function compareValue(rule, source, target, bundle, snapshots) {
    const operator = rule.operator;
    if (["equal", "digest-equal", "labels-equal"].includes(operator))
        return [canonicalJson(source) === canonicalJson(target), undefined];
    if (operator === "not-equal")
        return [canonicalJson(source) !== canonicalJson(target), undefined];
    if (operator === "in" || operator === "not-in") {
        if (!Array.isArray(target))
            return [false, "invalid"];
        const includes = target.some((value) => canonicalJson(value) === canonicalJson(source));
        return [operator === "in" ? includes : !includes, undefined];
    }
    if (operator === "subset" || operator === "superset") {
        if (!Array.isArray(source) || !Array.isArray(target))
            return [false, "invalid"];
        const left = new Set(source.map(canonicalJson)), right = new Set(target.map(canonicalJson));
        return [operator === "subset" ? [...left].every((value) => right.has(value)) : [...right].every((value) => left.has(value)), undefined];
    }
    if (operator === "labels-permutation") {
        const left = source.map(canonicalJson), right = target.map(canonicalJson);
        const sameLabels = JSON.stringify([...left].sort()) === JSON.stringify([...right].sort());
        return [sameLabels, JSON.stringify(left) === JSON.stringify(right) ? undefined : "none"];
    }
    if (operator === "unit-convertible") {
        if (source === target)
            return [true, undefined];
        const table = typeof bundle.units === "function" ? bundle.units() : undefined;
        if (table) {
            if (typeof source !== "string" || typeof target !== "string")
                return [false, "invalid"];
            try {
                const conversion = convertUnit(source, target, table);
                // Different dimensions are a contradiction; an unreadable or arbitrary unit is not decidable.
                return conversion === null ? [false, undefined] : [true, "none"];
            }
            catch {
                return [false, "unsupported"];
            }
        }
        // A bundle with no published units table cannot decide the question; that is undecidable,
        // not a statement that the two units differ.
        return [false, "unsupported"];
    }
    if (operator === "range") {
        if (typeof source !== "object" || source === null || Array.isArray(source) || typeof target !== "object" || target === null || Array.isArray(target))
            return [false, "invalid"];
        const sourceMin = source.minimum, sourceMax = source.maximum, targetMin = target.minimum, targetMax = target.maximum;
        if (![sourceMin, sourceMax, targetMin, targetMax].every((value) => typeof value === "number"))
            return [false, "invalid"];
        return [sourceMin >= targetMin && sourceMax <= targetMax, undefined];
    }
    if (operator === "pattern")
        return safePattern((rule.parameters ?? {}).pattern ?? target, source);
    if (operator === "same-dimension") {
        if (canonicalJson(source) === canonicalJson(target))
            return [true, undefined];
        if (typeof source === "string" && typeof target === "string") {
            const table = typeof bundle.units === "function" ? bundle.units() : undefined;
            if (!table)
                return [false, "unsupported"];
            try {
                // Sharing a dimension is exactly being convertible; an unreadable or arbitrary unit is
                // undecidable rather than proof of a shared dimension.
                return [convertUnit(source, target, table) !== null, undefined];
            }
            catch {
                return [false, "unsupported"];
            }
        }
        if (typeof source === "object" && source !== null && !Array.isArray(source) && typeof target === "object" && target !== null && !Array.isArray(target) && source.dimension !== undefined && target.dimension !== undefined)
            return [canonicalJson(source.dimension) === canonicalJson(target.dimension), undefined];
        return [false, "invalid"];
    }
    if (operator === "context-compatible") {
        // A source that declares no context is absent evidence, not a contradiction.
        if (source === "any" || source === "unspecified") {
            const open = target === null || target === undefined || target === "any" || target === "unspecified";
            return open ? [true, undefined] : [false, "unsupported"];
        }
        // A context value is not always a scalar: an intervention is a list of applied interventions.
        // Comparing those with === asks whether they are the same object, so two equal lists read as a
        // contradiction. Compare by value, which is what the Python engine has always done.
        const open = target === null || target === undefined || target === "any" || target === "unspecified";
        return [canonicalJson(source) === canonicalJson(target) || open, undefined];
    }
    if (operator === "namespace-version-compatible") {
        // Two releases of one namespace are not a contradiction. Identifiers are retired
        // and merged between releases, so what matters is what the transition did, and without a pinned
        // release-transition snapshot nobody can say: that is undecidable, not a mismatch. A transition
        // that retired and merged nothing preserves every identifier; one that did either is a real loss
        // and needs approval.
        if (source === target)
            return [true, undefined];
        const snapshot = snapshotFor(rule, snapshots.mappings);
        if (!snapshot)
            return [false, "unsupported"];
        for (const transition of (snapshot.transitions ?? [])) {
            if (!transition || typeof transition !== "object" || Array.isArray(transition))
                continue;
            if (String(transition.from) !== String(source) || String(transition.to) !== String(target))
                continue;
            const retired = transition.identifiers_retired ?? 0;
            const merged = transition.identifiers_merged ?? 0;
            if (!Number.isInteger(retired) || !Number.isInteger(merged))
                return [false, "invalid"];
            return [true, retired === 0 && merged === 0 ? "none" : "identifier-merge"];
        }
        // The snapshot is pinned but says nothing about this pair of releases.
        return [false, "unsupported"];
    }
    if (operator === "representation-equivalent") {
        // Re-encoding dense as sparse preserves the data only when both sides declare, and
        // agree on, what an absent entry means, the ordering, the shape and the dtype. Undeclared is
        // undecidable, not equivalent: in single-cell data a zero and an unobserved value are different
        // claims about the same cell.
        // The rule points at /contract/representation, so the finding keeps the representation
        // dimension rather than being filed against the contract as a whole.
        const left = (source ?? {}), right = (target ?? {});
        const sourceKind = left.kind, targetKind = right.kind;
        if (sourceKind === undefined || targetKind === undefined)
            return [false, "evidence"];
        if (sourceKind === targetKind)
            return [true, undefined];
        if (typeof sourceKind !== "string" || typeof targetKind !== "string")
            return [false, "invalid"];
        const pair = [sourceKind, targetKind].sort().join("|");
        // A dense and a sparse encoding of the same thing are re-encodings of each other. Any other
        // pair of kinds is a different structure, not a different encoding.
        const reEncodings = [["dense_vector", "sparse_vector"], ["matrix", "sparse_matrix"]].map((entry) => [...entry].sort().join("|"));
        if (!reEncodings.includes(pair))
            return [false, undefined];
        const enabling = (side) => [side.implicit_entry, side.ordering, side.sparsity];
        const sourceFields = enabling(left), targetFields = enabling(right);
        if (sourceFields.some((value) => value === undefined) || targetFields.some((value) => value === undefined))
            return [false, "evidence"];
        if (canonicalJson(sourceFields) !== canonicalJson(targetFields))
            return [false, undefined];
        return [true, "none"];
    }
    if (operator === "term-equivalent" || operator === "term-subsumes") {
        if (canonicalJson(source) === canonicalJson(target))
            return [true, undefined];
        const snapshot = snapshotFor(rule, snapshots.ontology);
        if (!snapshot)
            return [false, "unsupported"];
        return [operator === "term-equivalent" ? termEquivalent(source, target, snapshot) : termSubsumes(source, target, snapshot), undefined];
    }
    if (operator === "mapping-total" || operator === "mapping-bijective") {
        const snapshot = snapshotFor(rule, snapshots.mappings);
        if (!snapshot)
            return [false, "unsupported"];
        const bijective = operator === "mapping-bijective";
        if (!mappingMatches(source, target, snapshot, bijective))
            return [false, undefined];
        // A pinned mapping that is total over the declared universe and bijective on it
        // loses nothing, but it is still a conversion rather than a direct match. A mapping that is
        // total without being bijective merges identifiers, which needs approval.
        if (mappingMatches(source, target, snapshot, true))
            return [true, "none"];
        return [true, "identifier-merge"];
    }
    return [false, "unsupported"];
}
export function compareContracts(source, target, options = {}) {
    const bundle = options.bundle ?? getBundle();
    // Comparison normalises its own inputs, so a set-like field written in another order is not
    // reported as a contradiction by a caller who skipped the normalisation stage.
    source = normalised(source, bundle);
    target = normalised(target, bundle);
    const snapshots = { ontology: verifiedSnapshots(options.snapshots?.ontology), mappings: verifiedSnapshots(options.snapshots?.mappings) };
    let status;
    let findings;
    // Consent and data-use outcomes are collected apart from the technical findings,
    // and every path through this function reports them, including the ones with no rules to run.
    const policyFindings = [];
    if (source === null || target === null) {
        status = "UNKNOWN";
        findings = [finding("contract", "UNKNOWN", "BMCS_CONTRACT_NOT_DECLARED", "One or both ports have no compatibility contract.")];
    }
    else if (digest(source) === digest(target)) {
        status = "EXACT";
        findings = [finding("contract", "EXACT", "BMCS_EXACT_CONTRACT", "The two contracts are identical.")];
    }
    else {
        const refs = options.targetProfileRefs?.length ? options.targetProfileRefs : options.sourceProfileRefs ?? [];
        let rules = refs.length ? rulesFor(refs, bundle) : [];
        if (!rules.length) {
            for (const [family, members] of Object.entries(target)) {
                if (["profile_refs", "extensions"].includes(family) || typeof members !== "object" || members === null || Array.isArray(members))
                    continue;
                for (const name of Object.keys(members))
                    rules.push({ source: `/contract/${family}/${name}`, target: `/contract/${family}/${name}`, operator: family === "measurement" && ["unit", "units"].includes(name) ? "unit-convertible" : "equal", missing: "unknown", reason_code: "BMCS_VALUE_MISMATCH" });
            }
        }
        findings = [];
        let unknown = false, incompatible = false, conversion;
        for (const ref of [...new Set([...(options.sourceProfileRefs ?? []), ...(options.targetProfileRefs ?? [])])]) {
            let profile;
            try {
                profile = bundle.profile(ref);
            }
            catch {
                continue;
            }
            for (const [side, contract] of [["source", source], ["target", target]]) {
                for (const problem of unitKindErrors(bundle, profile, contract)) {
                    incompatible = true;
                    findings.push(finding("measurement", "INCOMPATIBLE", "BMCS_UNIT_DIMENSION_MISMATCH", `${side}: ${problem}`));
                }
            }
        }
        for (const rule of rules) {
            const left = getPointer({ contract: source }, rule.source), right = getPointer({ contract: target }, rule.target);
            const dimension = rule.target.split("/")[2] ?? "contract";
            if (rule.layer === "policy") {
                // Whether two ports may exchange data under their consent and data-use terms
                // is a governance outcome, not a statement about whether the data fit together. It is
                // reported, and the workspace policy stage decides what to do.
                if (left === undefined || right === undefined) {
                    if (rule.missing !== "ignore")
                        policyFindings.push(finding(dimension, "UNKNOWN", "BMCS_REQUIRED_EVIDENCE_MISSING", `${rule.target} is missing from the source or target contract.`));
                    continue;
                }
                const [allowed] = compareValue(rule, left, right, bundle, snapshots);
                policyFindings.push(finding(dimension, allowed ? "DIRECT_COMPATIBLE" : "INCOMPATIBLE", allowed ? "BMCS_RULE_SATISFIED" : rule.reason_code, `${rule.target}: '${rule.operator}' policy check ${allowed ? "passed" : "failed"}.`, allowed ? undefined : { source: left, target: right }));
                continue;
            }
            if (left === undefined || right === undefined) {
                if (rule.missing === "ignore")
                    continue;
                unknown = true;
                findings.push(finding(dimension, "UNKNOWN", "BMCS_REQUIRED_EVIDENCE_MISSING", `${rule.target} is missing from the source or target contract.`));
                continue;
            }
            const [compatible, transformation] = compareValue(rule, left, right, bundle, snapshots);
            if (transformation === "unsupported") {
                unknown = true;
                findings.push(finding(dimension, "UNKNOWN", "BMCS_OPERATOR_REQUIRES_SNAPSHOT", `The '${rule.operator}' check isn't available yet, so ${rule.target} can't be compared.`));
            }
            else if (transformation === "invalid") {
                unknown = true;
                findings.push(finding(dimension, "UNKNOWN", "BMCS_OPERATOR_INPUT_INVALID", `The '${rule.operator}' check received invalid or unsafe input at ${rule.target}.`));
            }
            else if (transformation === "evidence") {
                unknown = true;
                findings.push(finding(dimension, "UNKNOWN", "BMCS_REQUIRED_EVIDENCE_MISSING", `The '${rule.operator}' check needs a field neither contract declares at ${rule.target}.`));
            }
            else if (compatible) {
                conversion = transformation ?? conversion;
                findings.push(finding(dimension, "DIRECT_COMPATIBLE", "BMCS_RULE_SATISFIED", `${rule.target}: '${rule.operator}' check passed.`));
            }
            else {
                incompatible = true;
                findings.push(finding(dimension, "INCOMPATIBLE", rule.reason_code, `${rule.target}: '${rule.operator}' check failed.`, { source: left, target: right }));
            }
        }
        status = incompatible ? "INCOMPATIBLE" : unknown ? "UNKNOWN" : conversion === "none" ? "LOSSLESS_CONVERSION_AVAILABLE" : conversion ? "LOSSY_CONVERSION_REQUIRES_APPROVAL" : "DIRECT_COMPATIBLE";
    }
    const snapshotRefs = {
        ontology: [...snapshots.ontology.entries()].sort(([left], [right]) => left.localeCompare(right)).map(([ref, value]) => ({ ref, sha256: value.sha256 })),
        mappings: [...snapshots.mappings.entries()].sort(([left], [right]) => left.localeCompare(right)).map(([ref, value]) => ({ ref, sha256: value.sha256 })),
    };
    const partial = {
        schema_version: "0.1",
        standard: STANDARD,
        bundle_sha256: bundle.manifest.bundle_sha256,
        source: { contract_digest: source ? digest(source) : null, profile_refs: [...new Set(options.sourceProfileRefs ?? [])].sort() },
        target: { contract_digest: target ? digest(target) : null, profile_refs: [...new Set(options.targetProfileRefs ?? [])].sort() },
        status,
        policy_decision: (["LOSSY_CONVERSION_REQUIRES_APPROVAL", "INFERENCE_MODEL_REQUIRED", "CONDITIONAL"].includes(status) ? "APPROVAL_REQUIRED" : ["INCOMPATIBLE", "UNKNOWN"].includes(status) ? "BLOCK" : "ALLOW"),
        findings,
        policy_findings: policyFindings,
        ...((snapshotRefs.ontology.length || snapshotRefs.mappings.length) ? { snapshots: snapshotRefs } : {}),
    };
    return { ...partial, digest: digest(partial) };
}
function normalizeValue(value, pointer, setPaths) {
    if (Array.isArray(value)) {
        const normalized = value.map((child, index) => normalizeValue(child, `${pointer}/${index}`, setPaths));
        if (setPaths.has(pointer))
            normalized.sort((left, right) => canonicalJson(left).localeCompare(canonicalJson(right)));
        return normalized;
    }
    if (typeof value === "object" && value !== null) {
        return Object.fromEntries(Object.entries(value).map(([key, child]) => [key, normalizeValue(child, `${pointer}/${key}`, setPaths)]));
    }
    return value;
}
export function normalizeContract(contract, bundle = getBundle()) {
    ensureJsonLimits(contract, bundle.limits);
    const rules = bundle.readJson("rules/normalization.json");
    return normalizeValue(cloneJson(contract), "/contract", new Set(rules.set_like_paths));
}
export function normalizeManifest(manifest, bundle = getBundle()) {
    const findings = validateManifest(manifest, bundle);
    if (findings.length)
        throw new Error(`The manifest's compatibility block is invalid: ${findings.map((item) => `${item.path}: ${item.message}`).join("; ")}`);
    const result = cloneJson(manifest);
    if (!("compatibility" in result))
        return result;
    const compatibility = result.compatibility;
    compatibility.profiles = (compatibility.profiles ?? []).sort((left, right) => String(left.ref).localeCompare(String(right.ref)));
    const io = result.io;
    for (const direction of ["inputs", "outputs"]) {
        for (const port of (io?.[direction] ?? [])) {
            if (port.contract)
                port.contract = normalizeContract(port.contract, bundle);
            for (const accepted of (port.accepted_profiles ?? []))
                if (accepted.contract)
                    accepted.contract = normalizeContract(accepted.contract, bundle);
        }
    }
    return result;
}
export function buildCompatibilityLock(manifest, bundle = getBundle()) {
    const normalized = normalizeManifest(manifest, bundle);
    const imports = (normalized.compatibility?.profiles ?? []).sort((left, right) => String(left.ref).localeCompare(String(right.ref)));
    const contracts = [];
    const io = (normalized.io ?? {});
    for (const direction of ["inputs", "outputs"]) {
        for (const port of (io[direction] ?? [])) {
            if (!port.contract)
                continue;
            const contract = port.contract;
            contracts.push({ direction, port: port.name, contract, contract_digest: digest(contract) });
        }
    }
    contracts.sort((left, right) => `${left.direction}\0${left.port}`.localeCompare(`${right.direction}\0${right.port}`));
    const partial = {
        schema_version: "0.1",
        standard: STANDARD,
        bundle_sha256: bundle.manifest.bundle_sha256,
        contracts,
        resolved_references: imports,
        canonicalization: "RFC8785",
        components: { profile_count: imports.length, contract_count: contracts.length },
    };
    return { ...partial, digest: digest(partial) };
}
export const DEFAULT_RESOLUTION_LIMITS = { maxTransformations: 8, maxInferences: 2, maxExaminedEdges: 10_000 };
function capabilityKind(capability) {
    return "inferred_modality" in capability ? "inference" : "adapter";
}
function capabilityCost(path) {
    const ranks = { none: 0, bounded: 1, lossy: 2 };
    return [
        path.filter((item) => capabilityKind(item) === "inference").length,
        Math.max(0, ...path.map((item) => ranks[String(item.information_loss ?? "lossy")] ?? 2)),
        path.reduce((total, item) => total + Number(item.loss_score ?? 0), 0),
        path.length,
        path.reduce((total, item) => total + Number(item.execution_cost ?? 0), 0),
        path.map((item) => `${item.ref}#${item.sha256}`),
    ];
}
function compareCosts(left, right, includeIdentifiers = true) {
    for (let index = 0; index < (includeIdentifiers ? 6 : 5); index += 1) {
        const a = index === 5 ? left[5].join("\0") : left[index];
        const b = index === 5 ? right[5].join("\0") : right[index];
        if (a < b)
            return -1;
        if (a > b)
            return 1;
    }
    return 0;
}
const POLICY_STRENGTH = { allow: 0, approval: 1, block: 2 };
const PUBLISHED_TO_DECISION = { allow: "ALLOW", approval: "APPROVAL_REQUIRED", block: "BLOCK" };
/** The transformation policy published by the target contract's own profiles.
 *
 * Every profile publishes `transformation_policy`, and until now nothing read it: a profile that
 * declared `lossy: block` still produced APPROVAL_REQUIRED, because the only policy consulted was
 * the one a caller passed in by hand. Where a contract names several profiles the most restrictive
 * setting wins, since a profile that blocks a path is not overruled by one that permits it.
 */
function declaredPolicy(contract, bundle) {
    const refs = contract?.profile_refs;
    if (!Array.isArray(refs))
        return {};
    const combined = {};
    for (const ref of [...new Set(refs.filter((value) => typeof value === "string"))].sort()) {
        let profile;
        try {
            profile = bundle.profile(ref);
        }
        catch {
            continue;
        }
        const policy = profile?.transformation_policy;
        if (!policy || typeof policy !== "object" || Array.isArray(policy))
            continue;
        for (const [key, value] of Object.entries(policy)) {
            const current = combined[key];
            if (current === undefined || (POLICY_STRENGTH[String(value)] ?? 0) > (POLICY_STRENGTH[String(current)] ?? 0))
                combined[key] = String(value);
        }
    }
    return Object.fromEntries(Object.entries(combined).map(([key, value]) => [key, PUBLISHED_TO_DECISION[value] ?? value]));
}
function policyDecision(status, policy) {
    const key = { UNKNOWN: "unknown", CONDITIONAL: "conditional", LOSSLESS_CONVERSION_AVAILABLE: "lossless", LOSSY_CONVERSION_REQUIRES_APPROVAL: "lossy", INFERENCE_MODEL_REQUIRED: "inference" };
    const configured = key[status] ? policy[key[status]] : undefined;
    if (["ALLOW", "APPROVAL_REQUIRED", "BLOCK"].includes(String(configured)))
        return configured;
    if (["EXACT", "DIRECT_COMPATIBLE", "LOSSLESS_CONVERSION_AVAILABLE"].includes(status))
        return "ALLOW";
    if (["LOSSY_CONVERSION_REQUIRES_APPROVAL", "INFERENCE_MODEL_REQUIRED", "CONDITIONAL"].includes(status))
        return "APPROVAL_REQUIRED";
    return "BLOCK";
}
function technicalStatus(path) {
    if (path.some((item) => capabilityKind(item) === "inference"))
        return "INFERENCE_MODEL_REQUIRED";
    if (path.some((item) => ["bounded", "lossy"].includes(String(item.information_loss))))
        return "LOSSY_CONVERSION_REQUIRES_APPROVAL";
    return "LOSSLESS_CONVERSION_AVAILABLE";
}
function resolutionPlan(source, target, path, policy, bundle, snapshots) {
    const nodes = [{ id: "source", kind: "contract", contract_digest: digest(source) }];
    const edges = [];
    let previous = "source";
    path.forEach((capability, index) => {
        const kind = capabilityKind(capability);
        const id = `${kind}-${index + 1}`;
        nodes.push({ id, kind, ref: capability.ref, sha256: capability.sha256, information_loss: capability.information_loss ?? "lossy" });
        edges.push({ from: previous, to: id });
        previous = id;
    });
    nodes.push({ id: "target", kind: "contract", contract_digest: digest(target) });
    edges.push({ from: previous, to: "target" });
    const terminal = compareContracts(path.length ? path[path.length - 1].target : source, target, { bundle, snapshots });
    const ontologySnapshots = verifiedSnapshots(snapshots.ontology);
    const mappingSnapshots = verifiedSnapshots(snapshots.mappings);
    const snapshotReferences = [
        ...[...ontologySnapshots.entries()].sort(([left], [right]) => left.localeCompare(right)).map(([ref, value]) => ({ kind: "ontology_snapshot", ref, sha256: value.sha256 })),
        ...[...mappingSnapshots.entries()].sort(([left], [right]) => left.localeCompare(right)).map(([ref, value]) => ({ kind: "mapping_snapshot", ref, sha256: value.sha256 })),
    ];
    const status = path.length ? technicalStatus(path) : "DIRECT_COMPATIBLE";
    const partial = {
        schema_version: "0.1",
        standard: STANDARD,
        bundle_sha256: bundle.manifest.bundle_sha256,
        // The status the chain itself carries. reports[] holds the terminal comparison, which is EXACT
        // whenever the last adapter lands exactly on the target, so without this a reader cannot tell a
        // lossy chain from an inference one or from a direct match.
        technical_status: status,
        nodes,
        edges,
        reports: [{ digest: terminal.digest, status: terminal.status }],
        policy: { ...policy, decision: policyDecision(status, policy) },
        approvals: [],
        immutable_references: [...path.map((item) => ({ ref: item.ref, sha256: item.sha256 })), ...snapshotReferences],
    };
    return { ...partial, digest: digest(partial) };
}
export function resolveContracts(source, target, capabilities = [], options = {}) {
    const bundle = options.bundle ?? getBundle();
    // A policy the caller supplies wins; otherwise use the one the target's profiles publish.
    const policy = options.policy ?? declaredPolicy(target, options.bundle ?? getBundle());
    const snapshots = options.snapshots ?? {};
    const verified = {
        ontology: verifiedSnapshots(snapshots.ontology),
        mappings: verifiedSnapshots(snapshots.mappings),
    };
    const limits = { ...DEFAULT_RESOLUTION_LIMITS, ...(options.limits ?? {}) };
    const direct = compareContracts(source, target, { bundle, snapshots });
    const report = direct;
    if (!source || !target)
        return { resolution: "UNRESOLVED", report, reason: "UNKNOWN_CONTRACT" };
    if (["EXACT", "DIRECT_COMPATIBLE"].includes(direct.status))
        return { resolution: "RESOLVED", report, plan: resolutionPlan(source, target, [], policy, bundle, snapshots) };
    if (direct.status === "INCOMPATIBLE" && !capabilities.length)
        return { resolution: "UNRESOLVED", report, reason: "NO_CAPABILITY_PATH" };
    const reviewed = [];
    for (const capability of capabilities) {
        const schema = capabilityKind(capability) === "inference" ? "inference-capability.schema.json" : "adapter-capability.schema.json";
        const findings = validateObject(capability, schema, bundle);
        if (findings.length)
            throw new Error(`Invalid capability ${String(capability.ref ?? "<unknown>")}: ${findings.map((item) => item.message).join("; ")}`);
        if (capability.state === "reviewed")
            reviewed.push(capability);
    }
    const bySource = new Map();
    for (const capability of reviewed)
        bySource.set(digest(capability.source), [...(bySource.get(digest(capability.source)) ?? []), capability]);
    for (const values of bySource.values())
        values.sort((left, right) => `${left.ref}\0${left.sha256}`.localeCompare(`${right.ref}\0${right.sha256}`));
    const queue = [{ cost: capabilityCost([]), contract: source, path: [] }];
    const best = new Map([[digest(source), capabilityCost([])]]);
    const candidates = [];
    let examined = 0;
    while (queue.length && examined < limits.maxExaminedEdges) {
        queue.sort((left, right) => compareCosts(left.cost, right.cost));
        const current = queue.shift();
        const terminal = compareContracts(current.contract, target, { bundle, snapshots });
        if (["EXACT", "DIRECT_COMPATIBLE"].includes(terminal.status)) {
            candidates.push(current);
            continue;
        }
        if (current.path.length >= limits.maxTransformations)
            continue;
        for (const capability of bySource.get(digest(current.contract)) ?? []) {
            examined += 1;
            if (examined > limits.maxExaminedEdges)
                break;
            let preconditionsMet = true;
            for (const rule of (capability.preconditions ?? [])) {
                const left = getPointer({ contract: current.contract }, rule.source);
                const right = getPointer({ contract: capability.source }, rule.target);
                if (left === undefined || right === undefined) {
                    if (rule.missing !== "ignore") {
                        preconditionsMet = false;
                        break;
                    }
                    continue;
                }
                const [compatible, resultKind] = compareValue(rule, left, right, bundle, verified);
                if (!compatible || resultKind === "invalid" || resultKind === "unsupported") {
                    preconditionsMet = false;
                    break;
                }
            }
            if (!preconditionsMet)
                continue;
            const path = [...current.path, capability];
            if (path.filter((item) => capabilityKind(item) === "inference").length > limits.maxInferences)
                continue;
            const next = capability.target;
            const nextDigest = digest(next);
            if (current.path.some((item) => digest(item.source) === nextDigest))
                continue;
            const cost = capabilityCost(path);
            const previous = best.get(nextDigest);
            if (previous && compareCosts(previous, cost, false) < 0)
                continue;
            best.set(nextDigest, cost);
            queue.push({ cost, contract: next, path });
        }
    }
    if (!candidates.length)
        return { resolution: "UNRESOLVED", report, reason: examined >= limits.maxExaminedEdges ? "SEARCH_LIMIT_EXCEEDED" : "NO_CAPABILITY_PATH" };
    candidates.sort((left, right) => compareCosts(left.cost, right.cost));
    const equal = candidates.filter((item) => compareCosts(item.cost, candidates[0].cost, false) === 0);
    const plans = equal.map((item) => resolutionPlan(source, target, item.path, policy, bundle, snapshots));
    return plans.length > 1
        ? { resolution: "AMBIGUOUS", report, candidate_plans: plans, reason: "EQUAL_COST_SCIENTIFIC_PATHS" }
        : { resolution: "RESOLVED", report, plan: plans[0] };
}
export function parseYaml(text, limits = DEFAULT_RESOURCE_LIMITS) {
    if (utf8Bytes(text) > limits.maxDocumentBytes)
        throw new ResourceLimitError(`Document is ${utf8Bytes(text)} bytes; the limit is ${limits.maxDocumentBytes} bytes.`);
    const parsed = YAML.parse(text, { maxAliasCount: 100 });
    ensureJsonLimits(parsed, limits);
    if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed))
        throw new TypeError("The YAML document must contain an object at its root.");
    return parsed;
}

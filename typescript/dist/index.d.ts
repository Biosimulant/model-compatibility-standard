import { type UnitTable } from "./units.js";
export declare const STANDARD = "https://biosimulant.com/standards/model-compatibility/v0.1";
export type JsonValue = null | boolean | number | string | JsonValue[] | {
    [key: string]: JsonValue;
};
export type JsonObject = {
    [key: string]: JsonValue;
};
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
export declare const DEFAULT_RESOURCE_LIMITS: Readonly<ResourceLimits>;
export declare class ResourceLimitError extends Error {
}
export declare function ensureJsonLimits(value: unknown, limits?: ResourceLimits): void;
export type TechnicalStatus = "EXACT" | "DIRECT_COMPATIBLE" | "LOSSLESS_CONVERSION_AVAILABLE" | "LOSSY_CONVERSION_REQUIRES_APPROVAL" | "INFERENCE_MODEL_REQUIRED" | "CONDITIONAL" | "INCOMPATIBLE" | "UNKNOWN";
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
export declare class Bundle {
    readonly root: string;
    readonly limits: ResourceLimits;
    private readonly cache;
    constructor(root?: string, limits?: ResourceLimits);
    private path;
    readJson(relativePath: string): JsonObject;
    get manifest(): JsonObject;
    get catalogue(): JsonObject;
    profile(ref: string): JsonObject;
    profileSummary(ref: string): JsonObject | undefined;
    schemaFiles(): string[];
    units(): UnitTable | undefined;
    quantityKinds(): JsonObject;
    verifyIntegrity(): void;
}
export declare function getBundle(): Bundle;
export declare function canonicalJson(value: unknown): string;
export declare function digest(value: unknown): string;
export declare function validateContract(contract: JsonObject, profileRefs?: string[], bundle?: Bundle): ValidationFinding[];
export declare function validateObject(instance: JsonValue, schemaName: string, bundle?: Bundle): ValidationFinding[];
export declare function validateManifest(manifest: JsonObject, bundle?: Bundle): ValidationFinding[];
export interface ComparisonSnapshots {
    ontology?: JsonObject[];
    mappings?: JsonObject[];
}
export declare function compareContracts(source: JsonObject | null, target: JsonObject | null, options?: {
    sourceProfileRefs?: string[];
    targetProfileRefs?: string[];
    bundle?: Bundle;
    snapshots?: ComparisonSnapshots;
}): CompatibilityReport;
export declare function normalizeContract(contract: JsonObject, bundle?: Bundle): JsonObject;
export declare function normalizeManifest(manifest: JsonObject, bundle?: Bundle): JsonObject;
export declare function buildCompatibilityLock(manifest: JsonObject, bundle?: Bundle): JsonObject;
export interface ResolutionLimits {
    maxTransformations: number;
    maxInferences: number;
    maxExaminedEdges: number;
}
export declare const DEFAULT_RESOLUTION_LIMITS: Readonly<ResolutionLimits>;
export declare function resolveContracts(source: JsonObject | null, target: JsonObject | null, capabilities?: JsonObject[], options?: {
    policy?: JsonObject;
    limits?: Partial<ResolutionLimits>;
    bundle?: Bundle;
    snapshots?: ComparisonSnapshots;
}): JsonObject;
export declare function parseYaml(text: string, limits?: ResourceLimits): JsonObject;

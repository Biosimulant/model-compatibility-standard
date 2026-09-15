export declare const STANDARD = "https://biosimulant.com/standards/model-compatibility/v0.1";
export type JsonValue = null | boolean | number | string | JsonValue[] | {
    [key: string]: JsonValue;
};
export type JsonObject = {
    [key: string]: JsonValue;
};
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
export declare const DEFAULT_RESOURCE_LIMITS: Readonly<ResourceLimits>;
export declare class ResourceLimitError extends Error {
}
export declare function ensureJsonLimits(value: unknown, limits?: ResourceLimits): void;
export declare class BrowserBundle {
    readonly limits: ResourceLimits;
    private readonly files;
    constructor(files: Record<string, JsonObject>, limits?: ResourceLimits);
    readJson(relativePath: string): JsonObject;
    get catalogue(): JsonObject;
    profile(ref: string): JsonObject;
    profileSummary(ref: string): JsonObject | undefined;
    schemaFiles(): string[];
}
export declare function getBrowserBundle(): BrowserBundle;
export declare function validateObject(instance: JsonValue, schemaName: string, bundle?: BrowserBundle): ValidationFinding[];
export declare function validateContract(contract: JsonObject, profileRefs?: string[], bundle?: BrowserBundle): ValidationFinding[];
export declare function validateManifest(manifest: JsonObject, bundle?: BrowserBundle): ValidationFinding[];
export declare function parseYaml(text: string, limits?: ResourceLimits): JsonObject;

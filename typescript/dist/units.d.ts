export interface UnitTable {
    dimensions: string[];
    prefixes: Record<string, number>;
    aliases?: Record<string, string>;
    units: Record<string, {
        factor: number;
        dim: number[];
        metric?: boolean;
        offset?: number;
        arbitrary?: boolean;
    }>;
}
export interface Quantity {
    factor: number;
    dimension: number[];
    offset: number;
    arbitraryCodes: string[];
    codes: string[];
}
export interface Conversion {
    factor: number;
    offset: number;
    affine: boolean;
    lossless: boolean;
}
export declare class UnitError extends Error {
}
export declare function parseUnit(expression: string, table: UnitTable): Quantity;
/**
 * How to convert source into target, or null when the dimensions differ.
 * Throws UnitError when the question cannot be decided.
 */
export declare function convertUnit(source: string, target: string, table: UnitTable): Conversion | null;

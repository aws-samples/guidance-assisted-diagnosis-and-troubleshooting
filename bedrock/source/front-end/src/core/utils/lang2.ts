/**
 * @template T
 * @param {T} value
 * @returns {value is Exclude<T, null | undefined>}
 */

export function isNotNil<T>(value: T): value is Exclude<T, null | undefined> {
    return value != null;
}  
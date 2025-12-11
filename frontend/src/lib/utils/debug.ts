/**
 * Debug Logging Utilities
 *
 * Provides dev-only logging that's completely stripped in production builds.
 * Use these instead of raw console.log statements.
 */

const isDev = import.meta.env.DEV;

/**
 * Log a debug message (dev only)
 */
export function debug(prefix: string, ...args: unknown[]): void {
	if (isDev) {
		console.log(`[${prefix}]`, ...args);
	}
}

/**
 * Log a warning (dev only)
 */
export function debugWarn(prefix: string, ...args: unknown[]): void {
	if (isDev) {
		console.warn(`[${prefix}]`, ...args);
	}
}

/**
 * Log detailed debug info (dev only)
 */
export function debugVerbose(prefix: string, ...args: unknown[]): void {
	if (isDev) {
		console.debug(`[${prefix}]`, ...args);
	}
}

/**
 * Log an error (dev only)
 */
export function debugError(prefix: string, ...args: unknown[]): void {
	if (isDev) {
		console.error(`[${prefix}]`, ...args);
	}
}

/**
 * Create a scoped logger for a specific module
 */
export function createLogger(prefix: string) {
	return {
		log: (...args: unknown[]) => debug(prefix, ...args),
		warn: (...args: unknown[]) => debugWarn(prefix, ...args),
		debug: (...args: unknown[]) => debugVerbose(prefix, ...args),
		error: (...args: unknown[]) => debugError(prefix, ...args)
	};
}

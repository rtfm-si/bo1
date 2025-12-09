/**
 * Client-side hooks for SvelteKit.
 *
 * Handles client-side error reporting and other browser-specific hooks.
 */

import { initGlobalErrorHandlers, reportError } from '$lib/utils/errorReporter';

// Initialize global error handlers on module load
initGlobalErrorHandlers();

/**
 * Handle client-side navigation errors.
 *
 * Called when an error occurs during client-side navigation.
 */
export function handleError({ error, event }: { error: unknown; event: unknown }): void {
	// Report to backend
	const err = error instanceof Error ? error : new Error(String(error));
	reportError(err, {
		component: 'handleError',
		route: typeof event === 'object' && event && 'url' in event
			? String((event as { url: URL }).url.pathname)
			: undefined
	});

	// Log to console in development
	console.error('[SvelteKit Error]', error);
}

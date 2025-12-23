/**
 * Client-side hooks for SvelteKit.
 *
 * Handles client-side error reporting, chunk loading failures, and other browser-specific hooks.
 */

import { initGlobalErrorHandlers, reportError } from '$lib/utils/errorReporter';

// Initialize global error handlers on module load
initGlobalErrorHandlers();

/**
 * Storage key for reload attempt counter (prevents infinite reload loops)
 */
const RELOAD_ATTEMPTS_KEY = 'bo1_chunk_reload_attempts';
const MAX_RELOAD_ATTEMPTS = 3;
const RELOAD_WINDOW_MS = 60_000; // 1 minute window

/**
 * Check if an error is a chunk loading failure (dynamic import 404).
 * These occur when cached HTML references chunks that no longer exist after deploy.
 */
function isChunkLoadError(error: unknown): boolean {
	if (!(error instanceof Error)) return false;

	const message = error.message.toLowerCase();

	// Common patterns for chunk load failures
	return (
		message.includes('failed to fetch dynamically imported module') ||
		message.includes('loading chunk') ||
		message.includes('loading css chunk') ||
		message.includes("couldn't load module") ||
		(message.includes('failed to load') && message.includes('/_app/'))
	);
}

/**
 * Get reload attempt count within the current window.
 * Returns 0 if no recent attempts or window has expired.
 */
function getReloadAttempts(): number {
	try {
		const stored = sessionStorage.getItem(RELOAD_ATTEMPTS_KEY);
		if (!stored) return 0;

		const { count, timestamp } = JSON.parse(stored);
		const elapsed = Date.now() - timestamp;

		// Reset if window expired
		if (elapsed > RELOAD_WINDOW_MS) {
			sessionStorage.removeItem(RELOAD_ATTEMPTS_KEY);
			return 0;
		}

		return count;
	} catch {
		return 0;
	}
}

/**
 * Increment reload attempt counter.
 */
function incrementReloadAttempts(): void {
	try {
		const current = getReloadAttempts();
		sessionStorage.setItem(
			RELOAD_ATTEMPTS_KEY,
			JSON.stringify({
				count: current + 1,
				timestamp: Date.now()
			})
		);
	} catch {
		// Ignore storage errors
	}
}

/**
 * Clear reload attempts (called after successful navigation).
 */
function clearReloadAttempts(): void {
	try {
		sessionStorage.removeItem(RELOAD_ATTEMPTS_KEY);
	} catch {
		// Ignore storage errors
	}
}

/**
 * Handle chunk loading failure by triggering a page reload.
 * Shows a brief toast before reloading to inform the user.
 */
function handleChunkLoadFailure(): void {
	const attempts = getReloadAttempts();

	if (attempts >= MAX_RELOAD_ATTEMPTS) {
		// Too many attempts - don't reload, log error
		console.error('[Chunk Error] Max reload attempts reached, not reloading');
		reportError(new Error('Max chunk reload attempts reached'), {
			component: 'handleChunkLoadFailure',
			attempts: attempts.toString()
		});
		return;
	}

	incrementReloadAttempts();

	// Show brief toast to inform user (using console as fallback if toast isn't available)
	console.info('[Chunk Error] Page updated, reloading to fetch new version...');

	// Try to use the app's toast system if available
	try {
		const toastEvent = new CustomEvent('bo1:toast', {
			detail: {
				type: 'info',
				message: 'Page updated, reloading...',
				duration: 2000
			}
		});
		window.dispatchEvent(toastEvent);
	} catch {
		// Ignore if toast system not available
	}

	// Reload after brief delay to show toast
	setTimeout(() => {
		window.location.reload();
	}, 500);
}

// Clear reload attempts on successful page load
if (typeof window !== 'undefined') {
	window.addEventListener('load', clearReloadAttempts);
}

/**
 * Handle client-side navigation errors.
 *
 * Called when an error occurs during client-side navigation.
 * Detects chunk loading failures and triggers graceful reload.
 */
export function handleError({ error, event }: { error: unknown; event: unknown }): void {
	// Check for chunk loading failure first
	if (isChunkLoadError(error)) {
		handleChunkLoadFailure();
		return; // Don't report as error - reload will fix it
	}

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

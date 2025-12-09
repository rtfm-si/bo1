/**
 * Client-side error reporting utility.
 *
 * Reports JavaScript errors to the backend for logging and monitoring.
 * Debounced to prevent spam from repeated errors.
 */

import { env } from '$env/dynamic/public';
import { browser } from '$app/environment';

interface ErrorReport {
	error: string;
	stack?: string;
	url: string;
	component?: string;
	correlation_id?: string;
	context?: Record<string, unknown>;
}

// Track reported errors to avoid duplicates
const reportedErrors = new Set<string>();

// Debounce time for repeated errors (5 seconds)
const DEBOUNCE_MS = 5000;

/**
 * Report an error to the backend.
 *
 * @param error - The error object or message
 * @param context - Additional context about where the error occurred
 */
export async function reportError(
	error: Error | string,
	context?: { component?: string; [key: string]: unknown }
): Promise<void> {
	// Only report in browser
	if (!browser) return;

	const errorMessage = error instanceof Error ? error.message : error;
	const errorStack = error instanceof Error ? error.stack : undefined;

	// Create a hash for deduplication
	const errorHash = `${errorMessage}:${window.location.pathname}`;

	// Skip if recently reported
	if (reportedErrors.has(errorHash)) {
		return;
	}

	// Mark as reported (will be cleared after debounce period)
	reportedErrors.add(errorHash);
	setTimeout(() => reportedErrors.delete(errorHash), DEBOUNCE_MS);

	const report: ErrorReport = {
		error: errorMessage.slice(0, 1000), // Truncate long messages
		stack: errorStack?.slice(0, 10000),
		url: window.location.href,
		component: context?.component,
		context: context ? { ...context, component: undefined } : undefined
	};

	// Get correlation ID from any recent request header (if available)
	// This helps link frontend errors to backend requests

	try {
		const baseUrl = env.PUBLIC_API_URL || 'http://localhost:8000';
		await fetch(`${baseUrl}/api/errors`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(report),
			// Don't include credentials - this endpoint is public
			credentials: 'omit'
		});
	} catch {
		// Silently fail - don't cause additional errors when reporting errors
		console.debug('[errorReporter] Failed to report error:', errorMessage);
	}
}

/**
 * Initialize global error handlers.
 *
 * Call this once on app initialization to catch unhandled errors.
 */
export function initGlobalErrorHandlers(): void {
	if (!browser) return;

	// Handle uncaught errors
	window.addEventListener('error', (event) => {
		reportError(event.error || event.message, {
			component: 'window.onerror',
			filename: event.filename,
			lineno: event.lineno,
			colno: event.colno
		});
	});

	// Handle unhandled promise rejections
	window.addEventListener('unhandledrejection', (event) => {
		const error = event.reason instanceof Error ? event.reason : String(event.reason);
		reportError(error, {
			component: 'unhandledrejection'
		});
	});
}

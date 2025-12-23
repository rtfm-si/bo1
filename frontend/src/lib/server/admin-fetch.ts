/**
 * Server-side fetch helper for admin API calls.
 * Uses ADMIN_API_KEY for SSR authentication.
 */
import { env } from '$env/dynamic/private';

function getApiBaseUrl(): string {
	return env.INTERNAL_API_URL || 'http://api:8000';
}

function getAdminApiKey(): string | undefined {
	return env.ADMIN_API_KEY;
}

/**
 * Create headers for admin API requests.
 * Includes both cookie forwarding and API key authentication.
 */
export function adminHeaders(cookieHeader: string, csrfToken?: string): Record<string, string> {
	const headers: Record<string, string> = {
		'Cookie': cookieHeader
	};

	const apiKey = getAdminApiKey();
	if (apiKey) {
		headers['X-Admin-Key'] = apiKey;
	}

	if (csrfToken) {
		headers['X-CSRF-Token'] = csrfToken;
	}

	return headers;
}

/** Default timeout for SSR fetches (5 seconds) */
const SSR_FETCH_TIMEOUT_MS = 5000;

/** Delay between retries (100ms) */
const RETRY_DELAY_MS = 100;

/** Errors that are retryable */
const RETRYABLE_ERROR_CODES = ['ECONNREFUSED', 'ETIMEDOUT', 'ECONNRESET', 'EPIPE'];

/**
 * Check if an error is retryable (transient network issue).
 */
function isRetryableError(err: unknown): boolean {
	if (err instanceof Error) {
		const code = (err as NodeJS.ErrnoException).code;
		if (code && RETRYABLE_ERROR_CODES.includes(code)) {
			return true;
		}
		// AbortError from timeout is also retryable
		if (err.name === 'AbortError' || err.name === 'TimeoutError') {
			return true;
		}
	}
	return false;
}

/**
 * Fetch wrapper for admin API calls with proper auth headers.
 * Includes timeout and single retry for transient failures.
 */
export async function adminFetch(
	path: string,
	options: {
		method?: string;
		cookieHeader: string;
		csrfToken?: string;
		body?: unknown;
		timeout?: number;
		retries?: number;
	}
): Promise<Response> {
	const {
		method = 'GET',
		cookieHeader,
		csrfToken,
		body,
		timeout = SSR_FETCH_TIMEOUT_MS,
		retries = 1
	} = options;

	const headers: Record<string, string> = {
		...adminHeaders(cookieHeader, csrfToken)
	};

	if (body) {
		headers['Content-Type'] = 'application/json';
	}

	const doFetch = async (): Promise<Response> => {
		const controller = new AbortController();
		const timeoutId = setTimeout(() => controller.abort(), timeout);

		try {
			const fetchOptions: RequestInit = {
				method,
				headers,
				signal: controller.signal
			};

			if (body) {
				fetchOptions.body = JSON.stringify(body);
			}

			return await fetch(`${getApiBaseUrl()}${path}`, fetchOptions);
		} finally {
			clearTimeout(timeoutId);
		}
	};

	let lastError: unknown;
	for (let attempt = 0; attempt <= retries; attempt++) {
		try {
			return await doFetch();
		} catch (err) {
			lastError = err;
			if (attempt < retries && isRetryableError(err)) {
				// Brief delay before retry
				await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY_MS));
				console.warn(`[adminFetch] Retry ${attempt + 1}/${retries} for ${path}:`, err);
				continue;
			}
			throw err;
		}
	}

	// Should not reach here, but TypeScript needs it
	throw lastError;
}

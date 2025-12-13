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

/**
 * Fetch wrapper for admin API calls with proper auth headers.
 */
export async function adminFetch(
	path: string,
	options: {
		method?: string;
		cookieHeader: string;
		csrfToken?: string;
		body?: unknown;
	}
): Promise<Response> {
	const { method = 'GET', cookieHeader, csrfToken, body } = options;

	const headers: Record<string, string> = {
		...adminHeaders(cookieHeader, csrfToken)
	};

	if (body) {
		headers['Content-Type'] = 'application/json';
	}

	const fetchOptions: RequestInit = {
		method,
		headers
	};

	if (body) {
		fetchOptions.body = JSON.stringify(body);
	}

	return fetch(`${getApiBaseUrl()}${path}`, fetchOptions);
}

/**
 * SvelteKit Server Hooks
 *
 * Handles:
 * - API request proxying to backend
 */

import type { Handle } from '@sveltejs/kit';

// In Docker, use service name 'api' instead of localhost
// Outside Docker (dev), use localhost:8000
const API_BASE_URL = process.env.VITE_API_BASE_URL || process.env.PUBLIC_API_URL || 'http://api:8000';

export const handle: Handle = async ({ event, resolve }) => {
	// Proxy /api/* requests to backend
	if (event.url.pathname.startsWith('/api/')) {
		const backendUrl = `${API_BASE_URL}${event.url.pathname}${event.url.search}`;

		console.log(`[SvelteKit Proxy] ${event.request.method} ${event.url.pathname} -> ${backendUrl}`);

		try {
			// Forward the request to the backend
			const response = await fetch(backendUrl, {
				method: event.request.method,
				headers: event.request.headers,
				body: event.request.method !== 'GET' && event.request.method !== 'HEAD'
					? await event.request.arrayBuffer()
					: undefined,
			});

			// Create new response with backend response
			const responseBody = await response.arrayBuffer();

			return new Response(responseBody, {
				status: response.status,
				statusText: response.statusText,
				headers: response.headers,
			});
		} catch (error) {
			console.error(`[SvelteKit Proxy] Error proxying request:`, error);
			return new Response(JSON.stringify({ error: 'Proxy error' }), {
				status: 500,
				headers: { 'Content-Type': 'application/json' },
			});
		}
	}

	// For non-API requests, proceed normally
	return resolve(event);
};

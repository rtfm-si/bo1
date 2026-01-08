/**
 * SvelteKit Server Hooks
 *
 * Handles:
 * - API request proxying to backend
 */

import type { Handle } from '@sveltejs/kit';

// In Docker, use INTERNAL_API_URL (service name 'api') for server-side proxy
// This is for server-side requests, not browser requests
const API_BASE_URL = process.env.INTERNAL_API_URL || 'http://api:8000';
const DEBUG = process.env.NODE_ENV === 'development';

export const handle: Handle = async ({ event, resolve }) => {
	// Proxy /api/* requests to backend
	if (event.url.pathname.startsWith('/api/')) {
		const backendUrl = `${API_BASE_URL}${event.url.pathname}${event.url.search}`;

		try {
			// Forward the request to the backend
			const response = await fetch(backendUrl, {
				method: event.request.method,
				headers: event.request.headers,
				body: event.request.method !== 'GET' && event.request.method !== 'HEAD'
					? await event.request.arrayBuffer()
					: undefined,
			});

			if (DEBUG) {
				console.log(`[Proxy] ${event.request.method} ${event.url.pathname} -> ${response.status}`);
			}

			// Check if this is an SSE stream (text/event-stream)
			const contentType = response.headers.get('content-type');
			if (contentType && contentType.includes('text/event-stream')) {
				// For SSE, we need to stream the response body
				// Return the response directly with streaming support
				return new Response(response.body, {
					status: response.status,
					statusText: response.statusText,
					headers: response.headers,
				});
			}

			// For non-streaming responses, read the full body
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

	// For non-API requests, inject CSP header for HTML responses
	// This provides dev mode CSP consistency with production nginx
	let nonce: string | undefined;

	const response = await resolve(event, {
		transformPageChunk: ({ html }) => {
			// Extract nonce from SvelteKit's generated HTML
			const nonceMatch = html.match(/nonce="([^"]+)"/);
			if (nonceMatch) {
				nonce = nonceMatch[1];
			}
			return html;
		}
	});

	// Add CSP header to HTML responses (not assets/API)
	const contentType = response.headers.get('content-type');
	if (contentType?.includes('text/html') && nonce) {
		const csp = [
			`default-src 'self'`,
			`script-src 'self' 'nonce-${nonce}' https://analytics.boardof.one`,
			`style-src 'self' 'unsafe-inline'`,
			`img-src 'self' data: blob: https:`,
			`font-src 'self' data:`,
			`connect-src 'self' https: wss: http://localhost:* ws://localhost:*`,
			`frame-ancestors 'none'`,
			`base-uri 'self'`,
			`form-action 'self'`
		].join('; ');

		// Clone response to add header
		const newHeaders = new Headers(response.headers);
		newHeaders.set('Content-Security-Policy', csp);

		return new Response(response.body, {
			status: response.status,
			statusText: response.statusText,
			headers: newHeaders
		});
	}

	return response;
};

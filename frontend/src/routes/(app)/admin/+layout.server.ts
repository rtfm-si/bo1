/**
 * Admin layout server load guard - redirects non-admin users to dashboard.
 *
 * This runs on the server during SSR and prevents non-admin users from
 * accessing any /admin/* routes. The check happens before any page load.
 */
import { redirect } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';
import { env as publicEnv } from '$env/dynamic/public';
import type { LayoutServerLoad } from './$types';

function getApiBaseUrl(): string {
	return env.INTERNAL_API_URL || 'http://api:8000';
}

export const load: LayoutServerLoad = async ({ request, url }) => {
	// E2E mode: bypass server-side admin check (client-side auth is mocked)
	// The individual +page.server.ts files still make admin API calls
	// that will fail for non-admins in real auth scenarios
	if (publicEnv.PUBLIC_E2E_MODE === 'true') {
		return { isAdmin: true };
	}

	const cookieHeader = request.headers.get('cookie') || '';

	// No cookies = not authenticated
	if (!cookieHeader) {
		throw redirect(303, '/dashboard');
	}

	try {
		// Check user's admin status via API
		const response = await fetch(`${getApiBaseUrl()}/api/v1/auth/me`, {
			headers: {
				Cookie: cookieHeader
			}
		});

		if (!response.ok) {
			// Not authenticated or API error - redirect to dashboard
			console.warn(
				`Admin layout guard: API returned ${response.status} for ${url.pathname}`
			);
			throw redirect(303, '/dashboard');
		}

		const userData = await response.json();

		if (!userData.is_admin) {
			// User is authenticated but not an admin
			console.warn(
				`Admin layout guard: non-admin user ${userData.id} attempted to access ${url.pathname}`
			);
			throw redirect(303, '/dashboard');
		}

		// Admin verified - allow access
		return {
			isAdmin: true
		};
	} catch (error) {
		// Re-throw redirects
		if (error instanceof Response && error.status >= 300 && error.status < 400) {
			throw error;
		}

		// Handle redirect objects from SvelteKit
		if (
			typeof error === 'object' &&
			error !== null &&
			'status' in error &&
			'location' in error
		) {
			throw error;
		}

		// Any other error - fail closed (redirect to dashboard)
		console.error('Admin layout guard: error checking admin status', error);
		throw redirect(303, '/dashboard');
	}
};

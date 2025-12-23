import { error, isHttpError } from '@sveltejs/kit';
import { env } from '$env/dynamic/public';
import { adminFetch } from '$lib/server/admin-fetch';
import type { PageServerLoad } from './$types';

// Disable client-side preloading for this page to ensure fresh data
export const ssr = true;
export const prerender = false;

export const load: PageServerLoad = async ({ request }) => {
	// E2E mode: return mock stats (no backend available)
	if (env.PUBLIC_E2E_MODE === 'true') {
		return {
			stats: {
				totalUsers: 100,
				totalMeetings: 500,
				totalCost: 150.0,
				whitelistCount: 25,
				waitlistPending: 5
			}
		};
	}

	try {
		const cookieHeader = request.headers.get('cookie') || '';

		const response = await adminFetch('/api/admin/stats', {
			cookieHeader
		});

		if (!response.ok) {
			const errorText = await response.text();
			console.error('[admin/+page.server] Stats API error:', response.status, errorText);
			throw error(response.status, `Failed to load admin stats: ${errorText}`);
		}

		const statsData = await response.json();

		return {
			stats: {
				totalUsers: statsData.total_users || 0,
				totalMeetings: statsData.total_meetings || 0,
				totalCost: statsData.total_cost || 0,
				whitelistCount: statsData.whitelist_count || 0,
				waitlistPending: statsData.waitlist_pending || 0
			}
		};
	} catch (err) {
		// Re-throw SvelteKit HttpError to preserve original status code
		if (isHttpError(err)) {
			throw err;
		}
		console.error('[admin/+page.server] Unexpected error loading stats:', err);
		throw error(500, 'Failed to load admin stats');
	}
};

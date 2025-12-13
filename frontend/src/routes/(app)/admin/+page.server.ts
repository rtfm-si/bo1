import { error } from '@sveltejs/kit';
import { adminFetch } from '$lib/server/admin-fetch';
import type { PageServerLoad } from './$types';

// Disable client-side preloading for this page to ensure fresh data
export const ssr = true;
export const prerender = false;

export const load: PageServerLoad = async ({ request }) => {
	try {
		const cookieHeader = request.headers.get('cookie') || '';

		const response = await adminFetch('/api/admin/stats', {
			cookieHeader
		});

		if (!response.ok) {
			const errorText = await response.text();
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
		throw error(500, 'Failed to load admin stats');
	}
};

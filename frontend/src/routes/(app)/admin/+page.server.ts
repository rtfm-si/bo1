import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

const API_BASE_URL = process.env.INTERNAL_API_URL || 'http://api:8000';

// Disable client-side preloading for this page to ensure fresh data
export const ssr = true;
export const prerender = false;

export const load: PageServerLoad = async ({ cookies, request }) => {
	try {
		// Forward all cookies from the incoming request
		const cookieHeader = request.headers.get('cookie') || '';
		console.log('Loading admin stats with cookies:', cookieHeader ? 'present' : 'missing');

		const response = await fetch(`${API_BASE_URL}/api/admin/stats`, {
			headers: {
				'Cookie': cookieHeader
			}
		});

		console.log('Admin stats API status:', response.status);

		if (!response.ok) {
			const errorText = await response.text();
			console.error('Admin stats API returned:', response.status, errorText);
			throw error(response.status, `Failed to load admin stats: ${errorText}`);
		}

		const statsData = await response.json();

		console.log('Admin stats response:', JSON.stringify(statsData));

		const result = {
			stats: {
				totalUsers: statsData.total_users || 0,
				totalMeetings: statsData.total_meetings || 0,
				totalCost: statsData.total_cost || 0,
				whitelistCount: statsData.whitelist_count || 0,
				waitlistPending: statsData.waitlist_pending || 0
			}
		};

		console.log('Returning stats:', JSON.stringify(result));

		return result;
	} catch (err) {
		console.error('Failed to load admin stats:', err);
		throw error(500, 'Failed to load admin stats');
	}
};

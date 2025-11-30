import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

const API_BASE_URL = process.env.INTERNAL_API_URL || 'http://api:8000';

export const load: PageServerLoad = async ({ cookies }) => {
	try {
		// Fetch aggregated stats from dedicated endpoint
		const response = await fetch(`${API_BASE_URL}/api/admin/stats`, {
			headers: {
				'Cookie': cookies.getAll().map(c => `${c.name}=${c.value}`).join('; ')
			}
		});

		if (!response.ok) {
			console.error('Admin stats API returned:', response.status, await response.text());
			throw error(500, 'Failed to load admin stats');
		}

		const statsData = await response.json();

		return {
			stats: {
				totalUsers: statsData.total_users,
				totalMeetings: statsData.total_meetings,
				totalCost: statsData.total_cost,
				whitelistCount: statsData.whitelist_count,
				waitlistPending: statsData.waitlist_pending
			}
		};
	} catch (err) {
		console.error('Failed to load admin stats:', err);
		throw error(500, 'Failed to load admin stats');
	}
};

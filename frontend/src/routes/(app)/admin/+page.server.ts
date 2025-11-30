import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

const API_BASE_URL = process.env.INTERNAL_API_URL || 'http://api:8000';

export const load: PageServerLoad = async ({ cookies }) => {
	try {
		// Fetch stats from API - run in parallel
		const [usersResponse, whitelistResponse, waitlistResponse] = await Promise.all([
			fetch(`${API_BASE_URL}/api/admin/users?page=1&per_page=1`, {
				headers: {
					'Cookie': cookies.getAll().map(c => `${c.name}=${c.value}`).join('; ')
				}
			}),
			fetch(`${API_BASE_URL}/api/admin/beta-whitelist`, {
				headers: {
					'Cookie': cookies.getAll().map(c => `${c.name}=${c.value}`).join('; ')
				}
			}),
			fetch(`${API_BASE_URL}/api/admin/waitlist?status=pending`, {
				headers: {
					'Cookie': cookies.getAll().map(c => `${c.name}=${c.value}`).join('; ')
				}
			})
		]);

		if (!usersResponse.ok || !whitelistResponse.ok || !waitlistResponse.ok) {
			throw error(500, 'Failed to load admin stats');
		}

		const usersData = await usersResponse.json();
		const whitelistData = await whitelistResponse.json();
		const waitlistData = await waitlistResponse.json();

		// Calculate total cost from first page of users (as a sample)
		// In production, you might want a dedicated endpoint for this
		const totalCost = usersData.users.reduce((sum: number, u: any) => sum + (u.total_cost || 0), 0);

		return {
			stats: {
				totalUsers: usersData.total_count,
				totalMeetings: usersData.users[0]?.total_meetings || 0,
				totalCost: totalCost,
				whitelistCount: whitelistData.total_count,
				waitlistPending: waitlistData.pending_count
			}
		};
	} catch (err) {
		console.error('Failed to load admin stats:', err);
		throw error(500, 'Failed to load admin stats');
	}
};

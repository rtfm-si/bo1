import { error, fail } from '@sveltejs/kit';
import type { PageServerLoad, Actions } from './$types';

const API_BASE_URL = process.env.INTERNAL_API_URL || 'http://api:8000';

export const load: PageServerLoad = async ({ url, cookies }) => {
	const status = url.searchParams.get('status') || 'pending';

	const searchParams = new URLSearchParams();
	if (status) searchParams.set('status', status);

	try {
		const response = await fetch(`${API_BASE_URL}/api/admin/waitlist?${searchParams}`, {
			headers: {
				'Cookie': cookies.getAll().map(c => `${c.name}=${c.value}`).join('; ')
			}
		});

		if (!response.ok) {
			const errorData = await response.json().catch(() => ({ detail: 'Failed to load waitlist' }));
			throw error(response.status, errorData.detail || 'Failed to load waitlist');
		}

		const data = await response.json();

		return {
			entries: data.entries || [],
			totalCount: data.total_count || 0,
			pendingCount: data.pending_count || 0,
			statusFilter: status
		};
	} catch (err) {
		console.error('Failed to load waitlist:', err);
		throw error(500, 'Failed to load waitlist');
	}
};

export const actions: Actions = {
	approve: async ({ request, cookies }) => {
		const formData = await request.formData();
		const email = formData.get('email') as string;

		if (!email) {
			return fail(400, { error: 'Email is required' });
		}

		try {
			const response = await fetch(`${API_BASE_URL}/api/admin/waitlist/${encodeURIComponent(email)}/approve`, {
				method: 'POST',
				headers: {
					'Cookie': cookies.getAll().map(c => `${c.name}=${c.value}`).join('; ')
				}
			});

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({ detail: 'Failed to approve entry' }));
				return fail(response.status, { error: errorData.detail || 'Failed to approve entry' });
			}

			const result = await response.json();

			return {
				success: true,
				email: result.email,
				message: result.message
			};
		} catch (err) {
			console.error('Failed to approve entry:', err);
			return fail(500, { error: 'Failed to approve entry' });
		}
	}
};

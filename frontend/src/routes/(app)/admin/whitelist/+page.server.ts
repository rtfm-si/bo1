import { error, fail } from '@sveltejs/kit';
import type { PageServerLoad, Actions } from './$types';

const API_BASE_URL = process.env.INTERNAL_API_URL || 'http://api:8000';

export const load: PageServerLoad = async ({ request }) => {
	try {
		// Forward all cookies from the incoming request
		const cookieHeader = request.headers.get('cookie') || '';

		const response = await fetch(`${API_BASE_URL}/api/admin/beta-whitelist`, {
			headers: {
				'Cookie': cookieHeader
			}
		});

		if (!response.ok) {
			const errorData = await response.json().catch(() => ({ detail: 'Failed to load whitelist' }));
			throw error(response.status, errorData.detail || 'Failed to load whitelist');
		}

		const data = await response.json();

		return {
			entries: data.emails || [],
			envEmails: data.env_emails || [],
			totalCount: data.total_count || 0
		};
	} catch (err) {
		console.error('Failed to load whitelist:', err);
		throw error(500, 'Failed to load whitelist');
	}
};

export const actions: Actions = {
	add: async ({ request }) => {
		const formData = await request.formData();
		const email = formData.get('email') as string;
		const notes = formData.get('notes') as string | null;

		if (!email) {
			return fail(400, { error: 'Email is required' });
		}

		try {
			// Forward all cookies from the incoming request
			const cookieHeader = request.headers.get('cookie') || '';

			const response = await fetch(`${API_BASE_URL}/api/admin/beta-whitelist`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					'Cookie': cookieHeader
				},
				body: JSON.stringify({
					email,
					notes: notes || undefined
				})
			});

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({ detail: 'Failed to add email' }));
				return fail(response.status, { error: errorData.detail || 'Failed to add email' });
			}

			return { success: true };
		} catch (err) {
			console.error('Failed to add to whitelist:', err);
			return fail(500, { error: 'Failed to add email' });
		}
	},

	remove: async ({ request }) => {
		const formData = await request.formData();
		const email = formData.get('email') as string;

		if (!email) {
			return fail(400, { error: 'Email is required' });
		}

		try {
			// Forward all cookies from the incoming request
			const cookieHeader = request.headers.get('cookie') || '';

			const response = await fetch(`${API_BASE_URL}/api/admin/beta-whitelist/${encodeURIComponent(email)}`, {
				method: 'DELETE',
				headers: {
					'Cookie': cookieHeader
				}
			});

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({ detail: 'Failed to remove email' }));
				return fail(response.status, { error: errorData.detail || 'Failed to remove email' });
			}

			return { success: true };
		} catch (err) {
			console.error('Failed to remove from whitelist:', err);
			return fail(500, { error: 'Failed to remove email' });
		}
	}
};

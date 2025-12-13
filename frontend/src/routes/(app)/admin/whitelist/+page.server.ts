import { error, fail } from '@sveltejs/kit';
import { adminFetch } from '$lib/server/admin-fetch';
import type { PageServerLoad, Actions } from './$types';

export const load: PageServerLoad = async ({ request }) => {
	try {
		const cookieHeader = request.headers.get('cookie') || '';

		const response = await adminFetch('/api/admin/beta-whitelist', {
			cookieHeader
		});

		if (!response.ok) {
			const errorData = await response.json().catch(() => ({ detail: 'Failed to load whitelist' }));
			throw error(response.status, errorData.detail || 'Failed to load whitelist');
		}

		const data = await response.json();

		return {
			entries: data.emails || [],
			totalCount: data.total_count || 0
		};
	} catch (err) {
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
			const cookieHeader = request.headers.get('cookie') || '';

			const response = await adminFetch('/api/admin/beta-whitelist', {
				method: 'POST',
				cookieHeader,
				body: { email, notes: notes || undefined }
			});

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({ detail: 'Failed to add email' }));
				return fail(response.status, { error: errorData.detail || 'Failed to add email' });
			}

			return { success: true };
		} catch (err) {
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
			const cookieHeader = request.headers.get('cookie') || '';

			const response = await adminFetch(`/api/admin/beta-whitelist/${encodeURIComponent(email)}`, {
				method: 'DELETE',
				cookieHeader
			});

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({ detail: 'Failed to remove email' }));
				return fail(response.status, { error: errorData.detail || 'Failed to remove email' });
			}

			return { success: true };
		} catch (err) {
			return fail(500, { error: 'Failed to remove email' });
		}
	}
};

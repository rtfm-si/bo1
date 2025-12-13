import { error, fail } from '@sveltejs/kit';
import { adminFetch } from '$lib/server/admin-fetch';
import type { PageServerLoad, Actions } from './$types';

export const load: PageServerLoad = async ({ url, request }) => {
	const status = url.searchParams.get('status') || 'pending';

	const searchParams = new URLSearchParams();
	if (status) searchParams.set('status', status);

	try {
		const cookieHeader = request.headers.get('cookie') || '';

		const response = await adminFetch(`/api/admin/waitlist?${searchParams}`, {
			cookieHeader
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
			const cookieHeader = request.headers.get('cookie') || '';
			const csrfToken = cookies.get('csrf_token') || '';

			const response = await adminFetch(`/api/admin/waitlist/${encodeURIComponent(email)}/approve`, {
				method: 'POST',
				cookieHeader,
				csrfToken
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
			return fail(500, { error: 'Failed to approve entry' });
		}
	}
};

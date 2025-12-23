import { error, fail, isHttpError } from '@sveltejs/kit';
import { adminFetch } from '$lib/server/admin-fetch';
import type { PageServerLoad, Actions } from './$types';

export const load: PageServerLoad = async ({ url, request }) => {
	const page = parseInt(url.searchParams.get('page') || '1');
	const per_page = parseInt(url.searchParams.get('per_page') || '20');
	const email = url.searchParams.get('email') || '';

	const searchParams = new URLSearchParams();
	searchParams.set('page', page.toString());
	searchParams.set('per_page', per_page.toString());
	if (email) searchParams.set('email', email);

	try {
		const cookieHeader = request.headers.get('cookie') || '';

		const response = await adminFetch(`/api/admin/users?${searchParams}`, {
			cookieHeader
		});

		if (!response.ok) {
			const errorData = await response.json().catch(() => ({ detail: 'Failed to load users' }));
			console.error('[admin/users] API error:', response.status, errorData);
			throw error(response.status, errorData.detail || 'Failed to load users');
		}

		const data = await response.json();

		return {
			users: data.users,
			totalCount: data.total_count,
			page: data.page,
			perPage: data.per_page
		};
	} catch (err) {
		if (isHttpError(err)) {
			throw err;
		}
		console.error('[admin/users] Unexpected error:', err);
		throw error(500, 'Failed to load users');
	}
};

export const actions: Actions = {
	updateUser: async ({ request }) => {
		const formData = await request.formData();
		const userId = formData.get('userId') as string;
		const subscriptionTier = formData.get('subscription_tier') as string | null;
		const isAdmin = formData.get('is_admin') === 'true';

		if (!userId) {
			return fail(400, { error: 'User ID is required' });
		}

		const updateData: { subscription_tier?: string; is_admin?: boolean } = {};
		if (subscriptionTier) updateData.subscription_tier = subscriptionTier;
		updateData.is_admin = isAdmin;

		try {
			const cookieHeader = request.headers.get('cookie') || '';

			const response = await adminFetch(`/api/admin/users/${userId}`, {
				method: 'PATCH',
				cookieHeader,
				body: updateData
			});

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({ detail: 'Failed to update user' }));
				return fail(response.status, { error: errorData.detail || 'Failed to update user' });
			}

			return { success: true };
		} catch (err) {
			return fail(500, { error: 'Failed to update user' });
		}
	},

	lockUser: async ({ request }) => {
		const formData = await request.formData();
		const userId = formData.get('userId') as string;
		const reason = formData.get('reason') as string | null;

		if (!userId) {
			return fail(400, { error: 'User ID is required' });
		}

		try {
			const cookieHeader = request.headers.get('cookie') || '';

			const response = await adminFetch(`/api/admin/users/${userId}/lock`, {
				method: 'POST',
				cookieHeader,
				body: { reason }
			});

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({ detail: 'Failed to lock user' }));
				return fail(response.status, { error: errorData.detail || 'Failed to lock user' });
			}

			return { success: true, action: 'locked' };
		} catch (err) {
			return fail(500, { error: 'Failed to lock user' });
		}
	},

	unlockUser: async ({ request }) => {
		const formData = await request.formData();
		const userId = formData.get('userId') as string;

		if (!userId) {
			return fail(400, { error: 'User ID is required' });
		}

		try {
			const cookieHeader = request.headers.get('cookie') || '';

			const response = await adminFetch(`/api/admin/users/${userId}/unlock`, {
				method: 'POST',
				cookieHeader
			});

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({ detail: 'Failed to unlock user' }));
				return fail(response.status, { error: errorData.detail || 'Failed to unlock user' });
			}

			return { success: true, action: 'unlocked' };
		} catch (err) {
			return fail(500, { error: 'Failed to unlock user' });
		}
	},

	deleteUser: async ({ request }) => {
		const formData = await request.formData();
		const userId = formData.get('userId') as string;
		const hardDelete = formData.get('hard_delete') === 'true';

		if (!userId) {
			return fail(400, { error: 'User ID is required' });
		}

		try {
			const cookieHeader = request.headers.get('cookie') || '';

			const response = await adminFetch(`/api/admin/users/${userId}`, {
				method: 'DELETE',
				cookieHeader,
				body: { hard_delete: hardDelete, revoke_sessions: true }
			});

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({ detail: 'Failed to delete user' }));
				return fail(response.status, { error: errorData.detail || 'Failed to delete user' });
			}

			return { success: true, action: hardDelete ? 'hard_deleted' : 'soft_deleted' };
		} catch (err) {
			return fail(500, { error: 'Failed to delete user' });
		}
	}
};

import { error, fail } from '@sveltejs/kit';
import type { PageServerLoad, Actions } from './$types';

const API_BASE_URL = process.env.INTERNAL_API_URL || 'http://api:8000';

export const load: PageServerLoad = async ({ url, request }) => {
	const page = parseInt(url.searchParams.get('page') || '1');
	const per_page = parseInt(url.searchParams.get('per_page') || '20');
	const email = url.searchParams.get('email') || '';

	// Build query string
	const searchParams = new URLSearchParams();
	searchParams.set('page', page.toString());
	searchParams.set('per_page', per_page.toString());
	if (email) searchParams.set('email', email);

	try {
		// Forward all cookies from the incoming request
		const cookieHeader = request.headers.get('cookie') || '';

		const response = await fetch(`${API_BASE_URL}/api/admin/users?${searchParams}`, {
			headers: {
				'Cookie': cookieHeader
			}
		});

		if (!response.ok) {
			const errorData = await response.json().catch(() => ({ detail: 'Failed to load users' }));
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
			// Forward all cookies from the incoming request
			const cookieHeader = request.headers.get('cookie') || '';

			const response = await fetch(`${API_BASE_URL}/api/admin/users/${userId}`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json',
					'Cookie': cookieHeader
				},
				body: JSON.stringify(updateData)
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

			const response = await fetch(`${API_BASE_URL}/api/admin/users/${userId}/lock`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					'Cookie': cookieHeader
				},
				body: JSON.stringify({ reason })
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

			const response = await fetch(`${API_BASE_URL}/api/admin/users/${userId}/unlock`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					'Cookie': cookieHeader
				}
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

			const response = await fetch(`${API_BASE_URL}/api/admin/users/${userId}`, {
				method: 'DELETE',
				headers: {
					'Content-Type': 'application/json',
					'Cookie': cookieHeader
				},
				body: JSON.stringify({ hard_delete: hardDelete, revoke_sessions: true })
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

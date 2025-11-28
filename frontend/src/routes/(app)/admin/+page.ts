/**
 * Admin Dashboard - Auth Guard
 *
 * Checks if the user is an admin before allowing access to the admin dashboard.
 * Non-admin users are redirected to the home page.
 */

import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';
import { get } from 'svelte/store';
import { user } from '$lib/stores/auth';

export const load: PageLoad = async () => {
	const currentUser = get(user);

	// Redirect non-admins to home page
	if (!currentUser?.is_admin) {
		throw redirect(302, '/dashboard');
	}

	return {
		user: currentUser
	};
};

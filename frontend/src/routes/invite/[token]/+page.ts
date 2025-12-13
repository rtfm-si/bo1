/**
 * Load invitation data by token
 * Public endpoint - fetches invitation details for display
 */
import type { PageLoad } from './$types';
import { apiClient } from '$lib/api/client';
import type { InvitationResponse } from '$lib/api/types';

export const load: PageLoad = async ({ params }) => {
	const token = params.token;

	try {
		const invitation = await apiClient.getInvitation(token);
		return {
			invitation,
			token
		};
	} catch (err) {
		console.error('Failed to load invitation:', err);
		return {
			invitation: null as InvitationResponse | null,
			token,
			error: 'Invitation not found or has expired'
		};
	}
};

import { env } from '$env/dynamic/private';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export interface SharedSession {
	session_id: string;
	title: string;
	created_at: string;
	owner_name: string;
	expires_at: string;
	is_active: boolean;
	synthesis: unknown;
	conclusion: unknown;
	problem_context: Record<string, unknown>;
}

export const load: PageServerLoad = async ({ params, fetch }) => {
	const { token } = params;

	const apiUrl = env.API_URL || 'http://localhost:8000';

	try {
		const response = await fetch(`${apiUrl}/api/v1/share/${token}`);

		if (response.status === 404) {
			throw error(404, 'This share link does not exist or has been revoked.');
		}

		if (response.status === 410) {
			throw error(410, 'This share link has expired. Contact the owner for a new link.');
		}

		if (!response.ok) {
			throw error(500, 'Unable to load the shared meeting. Please try again later.');
		}

		const data: SharedSession = await response.json();

		return {
			session: data,
			token,
		};
	} catch (err) {
		// Check if it's a SvelteKit error (already thrown above)
		if (err && typeof err === 'object' && 'status' in err) {
			throw err;
		}

		console.error('Failed to load shared session:', err);
		throw error(500, 'Unable to connect to the server. Please try again later.');
	}
};

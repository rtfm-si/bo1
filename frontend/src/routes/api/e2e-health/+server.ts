/**
 * E2E test health check endpoint
 * Verifies that E2E mode is properly configured before running tests.
 * Used by CI to ensure environment variables are loaded correctly.
 */
import { json } from '@sveltejs/kit';
import { env } from '$env/dynamic/public';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async () => {
	const e2eMode = env.PUBLIC_E2E_MODE === 'true';

	return json({
		e2e_mode: e2eMode,
		api_url: env.PUBLIC_API_URL || null,
		ready: e2eMode,
		timestamp: new Date().toISOString()
	});
};
